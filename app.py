import atexit
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import gradio as gr
from smolagents.agents import MultiStepAgent

# from src.manager_agent import GradioManagerAgent
from src.utils import load_file
from ui_helpers import stream_to_gradio

preview_process = None
PREVIEW_PORT = 7861  # Internal port for preview apps
last_restart_time = 0  # Track when we last restarted the preview app
RESTART_COOLDOWN = 10  # Minimum seconds between restarts


def cleanup_preview_on_exit():
    """Cleanup function called on program exit."""
    print("🧹 Cleaning up preview app on exit...")
    stop_preview_app()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"🔔 Received signal {signum}, shutting down gracefully...")
    cleanup_preview_on_exit()
    sys.exit(0)


# Register signal handlers and exit handler
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
atexit.register(cleanup_preview_on_exit)


def get_preview_url():
    """Get the appropriate preview URL based on environment."""
    # In Docker/HF Spaces with nginx proxy, use the proxy path
    return "/preview/"


PREVIEW_URL = get_preview_url()


def is_port_available(port, host="0.0.0.0"):
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


def find_app_py_in_sandbox():
    """Find app.py file in sandbox folder and its subfolders."""
    sandbox_path = Path("sandbox")

    if not sandbox_path.exists():
        return None

    # Search for app.py files recursively
    app_files = list(sandbox_path.rglob("app.py"))

    if not app_files:
        return None

    # If multiple app.py files exist, throw an error
    if len(app_files) > 1:
        raise ValueError("Multiple app.py files found in sandbox directory")

    return str(app_files[0])


def save_file(path, new_text):
    if path is None:
        gr.Warning("⚠️ No file selected.")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        gr.Info(f"✅ Saved to: {path.split('sandbox/')[-1]}")
    except Exception as e:
        gr.Error(f"❌ Error saving: {e}")


def stop_preview_app():
    """Stop the preview app subprocess if it's running."""
    global preview_process
    if preview_process and preview_process.poll() is None:
        print(f"🛑 Stopping preview app process (PID: {preview_process.pid})...")
        try:
            preview_process.terminate()
            preview_process.wait(timeout=5)
            print("✅ Preview app stopped gracefully.")
        except subprocess.TimeoutExpired:
            preview_process.kill()
            # Wait a bit longer for the kill to take effect
            try:
                preview_process.wait(timeout=2)
                print("⚠️ Preview app force-killed after timeout.")
            except subprocess.TimeoutExpired:
                print("⚠️ Preview app may still be running after force-kill attempt.")
        except Exception as e:
            print(f"❌ Error stopping preview app: {e}")
        finally:
            preview_process = None


def start_preview_app():
    """Start the preview app in a subprocess if it's not already running."""
    global preview_process, last_restart_time

    # Check if preview app is already running and healthy
    if preview_process and preview_process.poll() is None:
        # Verify it's actually responsive on the port
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(("127.0.0.1", PREVIEW_PORT))
                if result == 0:
                    print(
                        f"✅ Preview app already running and healthy "
                        f"(PID: {preview_process.pid})"
                    )
                    return True, f"Preview running at {PREVIEW_URL}"
        except Exception:
            pass

    # Check cooldown period to avoid too frequent restarts
    current_time = time.time()
    if current_time - last_restart_time < RESTART_COOLDOWN:
        remaining_cooldown = RESTART_COOLDOWN - (current_time - last_restart_time)
        print(
            f"⏳ Preview app restart on cooldown, {remaining_cooldown:.1f}s remaining"
        )
        if preview_process and preview_process.poll() is None:
            # If there's still a process running, return success
            return True, f"Preview running at {PREVIEW_URL}"
        else:
            return (
                False,
                f"Preview app on cooldown for {remaining_cooldown:.1f} more seconds",
            )

    # Stop any existing process before starting a new one
    stop_preview_app()

    # Update restart time
    last_restart_time = current_time

    # Wait for the port to become available (up to 5 seconds)
    for i in range(10):  # 10 attempts * 0.5 seconds = 5 seconds max
        if is_port_available(PREVIEW_PORT):
            print(f"✅ Port {PREVIEW_PORT} is available")
            break
        print(f"⏳ Port {PREVIEW_PORT} still busy, waiting... (attempt {i+1}/10)")
        time.sleep(0.5)
    else:
        print(f"❌ Port {PREVIEW_PORT} is still not available after 5 seconds")
        return False, f"Port {PREVIEW_PORT} is not available"

    app_file = find_app_py_in_sandbox()
    if not app_file:
        return False, "No `app.py` found in the `sandbox` directory."

    print(f"🚀 Starting preview app from `{app_file}` on port {PREVIEW_PORT}...")
    try:
        # Change to the directory containing the app file
        app_dir = str(Path(app_file).parent)

        preview_process = subprocess.Popen(
            [
                "python",
                "app.py",
                "--server-port",
                str(PREVIEW_PORT),
                "--server-name",
                "0.0.0.0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=app_dir,  # Set working directory to the app directory
        )
        # Give it a moment to start up
        time.sleep(3)

        # Check if process is still running
        if preview_process.poll() is None:
            print(f"✅ Preview app started successfully (PID: {preview_process.pid}).")

            # Additional check: verify the process is actually listening on the port
            time.sleep(2)  # Give it a bit more time to fully initialize
            if preview_process.poll() is None:
                # Check if port is actually being used (reverse of availability check)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(1)
                        result = sock.connect_ex(("127.0.0.1", PREVIEW_PORT))
                        if result == 0:
                            print(
                                f"✅ Preview app is accepting connections on port "
                                f"{PREVIEW_PORT}"
                            )
                            return True, f"Preview running at {PREVIEW_URL}"
                        else:
                            print(
                                f"❌ Preview app started but not accepting connections "
                                f"on port {PREVIEW_PORT}"
                            )
                            # Get error output
                            try:
                                stdout, stderr = preview_process.communicate(timeout=1)
                                error_msg = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
                                print(f"Process output: {error_msg}")
                            except subprocess.TimeoutExpired:
                                print("Process still running but not responsive")
                            return False, "Preview app not accepting connections"
                except Exception as e:
                    print(f"❌ Error checking port connection: {e}")
                    return False, f"Error verifying connection: {e}"
            else:
                stdout, stderr = preview_process.communicate()
                error_msg = (
                    f"Process exited during initialization. "
                    f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
                )
                print(f"❌ {error_msg}")
                return False, f"Preview app crashed during startup:\n{error_msg}"
        else:
            stdout, stderr = preview_process.communicate()
            error_msg = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            print(f"❌ Failed to start preview app. Error:\n{error_msg}")
            return False, f"Failed to start preview app:\n{error_msg}"
    except Exception as e:
        print(f"❌ Exception while starting preview app: {e}")
        return False, f"Error starting preview app: {e}"


def create_iframe_preview():
    """Create an iframe that loads the sandbox app."""
    print("🔍 create_iframe_preview() called")

    # First, check if existing process is healthy
    if preview_process is not None:
        healthy, status = check_preview_health()
        print(f"🔍 Health check: {status}")
        if healthy:
            print("✅ Preview app is healthy, using existing process")
            iframe_html = (
                f'<iframe src="{PREVIEW_URL}" ' 'width="100%" height="500px"></iframe>'
            )
            return iframe_html
        else:
            print(f"⚠️ Preview app unhealthy: {status}, attempting restart...")
    else:
        print("🔍 No preview process exists, starting new one")

    # Try to start the preview app and show an iframe
    success, message = start_preview_app()
    print(f"🔍 start_preview_app() result: success={success}, message={message}")
    if success:
        iframe_html = (
            f'<iframe src="{PREVIEW_URL}" ' 'width="100%" height="500px"></iframe>'
        )
        return iframe_html
    else:
        # Show a more user-friendly error message with retry option
        error_html = f"""
        <div style="color: #d32f2f; padding: 20px; text-align: center;
                    border: 1px solid #d32f2f; border-radius: 8px;
                    background: #ffebee;">
            <h3>🚧 Preview App Temporarily Unavailable</h3>
            <p><strong>Status:</strong> {message}</p>
            <p>The preview app is starting up. Please wait a few seconds
            and try refreshing.</p>
            <button onclick="location.reload()" style="
                background: #1976d2; color: white; border: none;
                padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                Refresh Preview
            </button>
        </div>
        """
        print(f"🔍 Error in preview: {message}")
        return error_html


def is_preview_running():
    """Check if the preview app is running and accessible."""
    global preview_process

    # First check if process exists
    if preview_process is None or preview_process.poll() is not None:
        return False

    # Then check if it's actually responsive on the port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", PREVIEW_PORT))
            return result == 0
    except Exception:
        return False


def check_preview_health():
    """Check if the preview app is healthy and restart if needed."""
    global preview_process

    if preview_process is None:
        return False, "No preview process"

    if preview_process.poll() is not None:
        # Process has exited
        try:
            stdout, stderr = preview_process.communicate()
            error_msg = f"Process exited. STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            print(f"🚨 Preview process died: {error_msg}")
        except Exception as e:
            print(f"🚨 Preview process died: {e}")
        preview_process = None
        return False, "Process died"

    # Check if responsive with multiple attempts and longer timeout
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)  # Increased timeout from 1 to 3 seconds
                result = sock.connect_ex(("127.0.0.1", PREVIEW_PORT))
                if result == 0:
                    return True, "Healthy"
                else:
                    if attempt < max_attempts - 1:
                        print(
                            f"🔍 Health check attempt {attempt + 1}/"
                            f"{max_attempts} failed, retrying..."
                        )
                        time.sleep(1)  # Wait before retrying
                    else:
                        return False, "Not responsive on port after multiple attempts"
        except Exception as e:
            if attempt < max_attempts - 1:
                print(
                    f"🔍 Health check attempt {attempt + 1}/"
                    f"{max_attempts} failed with error: {e}, retrying..."
                )
                time.sleep(1)
            else:
                return False, f"Connection check failed: {e}"

    return False, "Health check failed"


def ensure_preview_running():
    """Ensure the preview app is running, start it if needed."""
    if not is_preview_running():
        start_preview_app()


def get_default_model_for_provider(provider: str) -> str:
    """Get the default model ID for a given provider."""
    provider_model_map = {
        "Anthropic": "anthropic/claude-sonnet-4-20250514",
        "OpenAI": "openai/gpt-4o",
        "Mistral": "mistral/codestral-latest",
        "SambaNova": "sambanova/Meta-Llama-3.1-70B-Instruct",
        "Hugging Face": "huggingface/together/Qwen/Qwen2.5-Coder-32B-Instruct",
    }
    return provider_model_map.get(
        provider, "huggingface/together/Qwen/Qwen2.5-Coder-32B-Instruct"
    )


def save_api_key(provider, api_key):
    """Save API key to environment variable and update model accordingly."""
    if not api_key.strip():
        return f"⚠️ Please enter a valid API key for {provider}"

    # Map provider names to environment variable names
    env_var_map = {
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Hugging Face": "HUGGINGFACE_API_KEY",
        "SambaNova": "SAMBANOVA_API_KEY",
        "Mistral": "MISTRAL_API_KEY",
    }

    env_var_name = env_var_map.get(provider)
    if env_var_name:
        # Always set the provider-specific API key
        os.environ[env_var_name] = api_key.strip()

        # For non-Hugging Face providers, also set the generic API_KEY and MODEL_ID
        # This ensures the main agent uses the correct model and API key
        if provider != "Hugging Face":
            os.environ["API_KEY"] = api_key.strip()
            os.environ["MODEL_ID"] = get_default_model_for_provider(provider)
            return (
                f"✅ {provider} API key saved successfully \n"
                f"Model: {get_default_model_for_provider(provider)}"
            )
        else:
            return f"✅ {provider} API key saved successfully"
    else:
        return f"❌ Unknown provider: {provider}"


def get_api_key_status(selected_llm_provider="Anthropic"):
    """Get the status of Hugging Face and selected LLM provider API keys."""
    env_vars = {
        "Hugging Face": "HUGGINGFACE_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "SambaNova": "SAMBANOVA_API_KEY",
        "Mistral": "MISTRAL_API_KEY",
    }

    status = []

    # Always show Hugging Face status
    hf_env_var = env_vars["Hugging Face"]
    if os.getenv(hf_env_var):
        key = os.getenv(hf_env_var)
        masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        status.append(f"✅ Hugging Face: {masked_key}")
    else:
        status.append("❌ Hugging Face: Not set")

    # Show selected LLM provider status
    llm_env_var = env_vars.get(selected_llm_provider)
    if llm_env_var and os.getenv(llm_env_var):
        key = os.getenv(llm_env_var)
        masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        model = get_default_model_for_provider(selected_llm_provider)
        status.append(f"✅ {selected_llm_provider}: {masked_key} (Model: {model})")
    else:
        model = get_default_model_for_provider(selected_llm_provider)
        status.append(f"❌ {selected_llm_provider}: Not set (Would use: {model})")

    # Show current active model
    current_model = os.getenv("MODEL_ID", "Qwen/Qwen2.5-Coder-32B-Instruct")
    status.append(f"🤖 Current Active Model: {current_model}")

    return "\n".join(status)


class GradioUI:
    """A one-line interface to launch your agent in Gradio"""

    def __init__(self, agent: MultiStepAgent):
        self.agent = agent
        self.parent_id = None

    def interact_with_agent(self, prompt, messages, session_state):
        import gradio as gr

        self.parent_id = int(time.time() * 1000)
        # Get the agent type from the template agent
        if "agent" not in session_state:
            session_state["agent"] = self.agent

        try:
            messages.append(
                gr.ChatMessage(role="user", content=prompt, metadata={"status": "done"})
            )
            messages.append(
                gr.ChatMessage(
                    role="assistant",
                    content="",
                    metadata={
                        "id": self.parent_id,
                        "title": "🧠 Thinking...",
                        "status": "pending",
                    },
                )
            )
            start_time = time.time()
            yield messages

            for msg in stream_to_gradio(
                session_state["agent"],
                task=prompt,
                reset_agent_memory=False,
                parent_id=self.parent_id,
            ):
                if isinstance(msg, gr.ChatMessage):
                    messages.append(msg)
                    messages[-1].metadata["status"] = "done"
                    if msg.content.startswith("**Final answer:**"):
                        # Remove "**Final answer:**" prefix from the message content
                        if msg.content.startswith("**Final answer:**"):
                            msg.content = msg.content.replace("**Final answer:**\n", "")
                        # Set the parent message status to done when final
                        # answer is reached
                        for message in messages:
                            if (
                                isinstance(message, gr.ChatMessage)
                                and message.metadata.get("id") == self.parent_id
                            ):
                                message.metadata["status"] = "done"
                                message.metadata["title"] = (
                                    f"🧠 Thought for {time.time() - start_time:.0f} "
                                    "sec."
                                )
                                break
                elif isinstance(msg, str):  # Then it's only a completion delta
                    msg = msg.replace("<", r"\<").replace(
                        ">", r"\>"
                    )  # HTML tags seem to break Gradio Chatbot
                    if messages[-1].metadata["status"] == "pending":
                        messages[-1].content = msg
                    else:
                        messages.append(
                            gr.ChatMessage(
                                role="assistant",
                                content=msg,
                                metadata={"status": "pending"},
                            )
                        )
                yield messages

            yield messages
        except Exception as e:
            yield messages
            raise gr.Error(f"Error in interaction: {str(e)}") from e

    def log_user_message(self, text_input, file_uploads_log):
        import gradio as gr

        return (
            text_input
            + (
                f"\nYou have been provided with these files, which might be "
                f"helpful or not: {file_uploads_log}"
                if len(file_uploads_log) > 0
                else ""
            ),
            "",
            gr.Button(interactive=False),
        )

    def launch(self, share: bool = True, **kwargs):
        self.create_app().launch(debug=True, share=share, **kwargs)

    def create_app(self):
        import gradio as gr

        with gr.Blocks(
            title="💗Likable",
            theme=gr.themes.Soft(),
            fill_height=True,
            fill_width=True,
        ) as demo:
            gr.Markdown("# 💗Likable")

            with gr.Row(elem_classes="main-container"):
                # Left side - Chat Interface
                with gr.Column(scale=1, elem_classes="chat-container"):
                    avatar_url = (
                        "http://em-content.zobj.net/source/apple/419/"
                        "growing-heart_1f497.png"
                    )
                    chatbot = gr.Chatbot(
                        avatar_images=(None, avatar_url),
                        type="messages",
                        resizable=True,
                        height="70vh",
                    )

                    with gr.Column():
                        text_input = gr.Textbox(
                            placeholder="Ask Likable...",
                            scale=4,
                            container=False,
                        )
                        submit_btn = gr.Button("↑", size="sm", variant="primary")

                # Right side - Preview/Code/Settings Toggle
                with gr.Column(scale=4, elem_classes="preview-container"):
                    with gr.Tab("Preview"):
                        iframe_url = (
                            f'<iframe src="{PREVIEW_URL}" '
                            'width="100%" height="500px"></iframe>'
                        )
                        preview_html = gr.HTML(
                            value=iframe_url,
                            elem_id="preview-container",
                        )

                    with gr.Tab("Code"):
                        with gr.Row():
                            save_btn = gr.Button("Save", size="sm")
                        with gr.Row(equal_height=True):
                            file_explorer = gr.FileExplorer(
                                scale=1,
                                file_count="single",
                                value="app.py",
                                root_dir="sandbox",
                            )

                            code_editor = gr.Code(
                                scale=3,
                                value=load_file("sandbox/app.py"),
                                language="python",
                                visible=True,
                                interactive=True,
                                autocomplete=True,
                            )

                    with gr.Tab("Settings"):
                        gr.Markdown("## 🔑 API Keys")
                        gr.Markdown(
                            "Configure your API keys for different AI providers:"
                        )

                        # API Key Status Display
                        api_status = gr.Textbox(
                            label="Current API Key Status",
                            value=get_api_key_status(),
                            interactive=False,
                            lines=4,
                            max_lines=4,
                        )

                        # with gr.Row():
                        #     refresh_status_btn = gr.Button(
                        #         "🔄 Refresh Status", size="sm"
                        #     )

                        gr.Markdown("---")

                        # Hugging Face Token
                        with gr.Row():
                            hf_token = gr.Textbox(
                                label="Hugging Face Token",
                                placeholder="hf_...",
                                type="password",
                                scale=4,
                            )
                            hf_save_btn = gr.Button("Save", size="sm", scale=1)

                        gr.Markdown("---")

                        # LLM Token with Provider Selection
                        with gr.Row():
                            llm_provider = gr.Dropdown(
                                label="LLM Provider",
                                choices=["Anthropic", "OpenAI", "Mistral", "SambaNova"],
                                value="Anthropic",
                                scale=1,
                            )
                            llm_token = gr.Textbox(
                                label="LLM Token",
                                placeholder="Enter your API key...",
                                type="password",
                                scale=3,
                            )
                            llm_save_btn = gr.Button("Save", size="sm", scale=1)

                        # Status message for API key operations
                        api_message = gr.Textbox(
                            label="Status", interactive=False, visible=False
                        )

            # Add session state to store session-specific data
            session_state = gr.State({})
            stored_messages = gr.State([])
            file_uploads_log = gr.State([])

            # Set up event handlers for API key saving
            def save_and_update_status(
                provider, api_key, selected_llm_provider="Anthropic", session_state=None
            ):
                message = save_api_key(provider, api_key)
                status = get_api_key_status(selected_llm_provider)

                # If this is an LLM provider (not Hugging Face), recreate the agent
                if provider != "Hugging Face" and session_state is not None:
                    agent_message = self.recreate_agent_with_new_model(
                        session_state, provider
                    )
                    if agent_message:
                        message += f"\n{agent_message}"

                return message, status, ""  # Clear the input field

            hf_save_btn.click(
                lambda key, llm_prov, sess_state: save_and_update_status(
                    "Hugging Face", key, llm_prov, sess_state
                ),
                inputs=[hf_token, llm_provider, session_state],
                outputs=[api_message, api_status, hf_token],
            ).then(lambda: gr.Textbox(visible=True), outputs=[api_message])

            llm_save_btn.click(
                lambda provider, key, sess_state: save_and_update_status(
                    provider, key, provider, sess_state
                ),
                inputs=[llm_provider, llm_token, session_state],
                outputs=[api_message, api_status, llm_token],
            ).then(lambda: gr.Textbox(visible=True), outputs=[api_message])

            # refresh_status_btn.click(
            #     fn=lambda llm_prov: get_api_key_status(llm_prov),
            #     inputs=[llm_provider],
            #     outputs=[api_status],
            # )

            # Update status when LLM provider dropdown changes
            llm_provider.change(
                fn=get_api_key_status, inputs=[llm_provider], outputs=[api_status]
            )

            # Set up event handlers
            file_explorer.change(
                fn=load_file, inputs=file_explorer, outputs=code_editor
            )

            def refresh_all_with_preview_restart():
                """Refresh everything including forcing a preview app restart
                to pick up code changes."""
                print("🔄 Forcing preview app restart to pick up code changes...")
                # Force stop the current preview app to pick up code changes
                stop_preview_app()
                # Start fresh with new code
                current_preview = create_iframe_preview()

                # Update the file explorer and code editor
                file_explorer_val = gr.FileExplorer(
                    scale=1,
                    file_count="single",
                    value="app.py",
                    root_dir="sandbox",
                )
                code_editor_val = gr.Code(
                    scale=3,
                    value=load_file("sandbox/app.py"),
                    language="python",
                    visible=True,
                    interactive=True,
                    autocomplete=True,
                )
                return file_explorer_val, code_editor_val, current_preview

            def refresh_all():
                # Only refresh preview if it's not currently healthy
                current_preview = None
                if preview_process is not None:
                    healthy, status = check_preview_health()
                    if healthy:
                        # Preview is healthy, just return existing iframe
                        current_preview = (
                            f'<iframe src="{PREVIEW_URL}" '
                            'width="100%" height="500px"></iframe>'
                        )
                    else:
                        # Preview needs refresh
                        current_preview = create_iframe_preview()
                else:
                    # No preview process, create one
                    current_preview = create_iframe_preview()

                # Then, update the file explorer and code editor
                file_explorer_val = gr.FileExplorer(
                    scale=1,
                    file_count="single",
                    value="app.py",
                    root_dir="sandbox",
                )
                code_editor_val = gr.Code(
                    scale=3,
                    value=load_file("sandbox/app.py"),
                    language="python",
                    visible=True,
                    interactive=True,
                    autocomplete=True,
                )
                return file_explorer_val, code_editor_val, current_preview

            save_btn.click(
                fn=save_file,
                inputs=[file_explorer, code_editor],
            ).then(
                fn=refresh_all_with_preview_restart,
                outputs=[file_explorer, code_editor, preview_html],
            )

            text_input.submit(
                self.log_user_message,
                [text_input, file_uploads_log],
                [stored_messages, text_input, submit_btn],
            ).then(
                self.interact_with_agent,
                [stored_messages, chatbot, session_state],
                [chatbot],
            ).then(
                fn=refresh_all_with_preview_restart,
                outputs=[file_explorer, code_editor, preview_html],
            ).then(
                lambda: (
                    gr.Textbox(
                        interactive=True,
                        placeholder="Ask Likable...",
                    ),
                    gr.Button(interactive=True),
                ),
                None,
                [text_input, submit_btn],
            )

            submit_btn.click(
                self.log_user_message,
                [text_input, file_uploads_log],
                [stored_messages, text_input, submit_btn],
            ).then(
                self.interact_with_agent,
                [stored_messages, chatbot, session_state],
                [chatbot],
            ).then(
                fn=refresh_all_with_preview_restart,
                outputs=[file_explorer, code_editor, preview_html],
            ).then(
                lambda: (
                    gr.Textbox(
                        interactive=True,
                        placeholder="Ask Likable....",
                    ),
                    gr.Button(interactive=True),
                ),
                None,
                [text_input, submit_btn],
            )

            # Load the preview iframe when the app starts
            demo.load(fn=create_iframe_preview, outputs=[preview_html])

            # Note: Removed demo.unload(stop_preview_app) as it was causing
            # preview app restarts on every page reload, leading to 502 errors.
            # We have proper cleanup via signal handlers and atexit handlers.

        return demo

    def recreate_agent_with_new_model(self, session_state, provider=None):
        """Recreate the agent with updated model configuration."""
        from kiss_agent import KISSAgent

        # Get the new model ID if provider is specified
        if provider and provider != "Hugging Face":
            model_id = get_default_model_for_provider(provider)

            # Get API key from provider-specific environment variable
            env_var_map = {
                "Anthropic": "ANTHROPIC_API_KEY",
                "OpenAI": "OPENAI_API_KEY",
                "SambaNova": "SAMBANOVA_API_KEY",
                "Mistral": "MISTRAL_API_KEY",
            }

            env_var_name = env_var_map.get(provider)
            api_key = os.getenv(env_var_name) if env_var_name else None

            if not api_key:
                return f"❌ No API key found for {provider}"

            # Create new agent with updated model
            new_agent = KISSAgent(model_id=model_id, api_key=api_key)
            session_state["agent"] = new_agent

            return f"🔄 Agent updated to use {provider} model: {model_id}"
        return ""


if __name__ == "__main__":
    import sys

    from kiss_agent import KISSAgent

    agent = KISSAgent()

    # Start the preview app automatically when the main app starts
    print("🚀 Starting preview app automatically...")
    success, message = start_preview_app()
    if success:
        print(f"✅ Preview app started: {message}")
    else:
        print(f"❌ Failed to start preview app: {message}")

    # Parse command line arguments for server configuration
    server_port = 7860  # default
    server_name = "127.0.0.1"  # default

    if "--server-port" in sys.argv:
        port_idx = sys.argv.index("--server-port")
        if port_idx + 1 < len(sys.argv):
            server_port = int(sys.argv[port_idx + 1])

    if "--server-name" in sys.argv:
        name_idx = sys.argv.index("--server-name")
        if name_idx + 1 < len(sys.argv):
            server_name = sys.argv[name_idx + 1]

    GradioUI(agent).launch(
        share=False, server_port=server_port, server_name=server_name
    )
