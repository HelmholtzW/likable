import os
import subprocess
import sys
import time
from pathlib import Path

import gradio as gr
import requests
from smolagents.agents import MultiStepAgent

# from src.manager_agent import GradioManagerAgent
from src.utils import load_file
from ui_helpers import stream_to_gradio

preview_process = None
PREVIEW_PORT = 7861  # Different port from main app


def get_preview_url():
    """Get the appropriate preview URL based on environment."""
    # For Hugging Face Spaces with nginx proxy, use the /preview/ path
    if os.getenv("SPACE_ID") or os.getenv("HF_SPACE"):
        return "/preview/"
    # Check if running in Docker
    elif os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
        # In Docker with nginx proxy, use relative path
        return "/preview/"
    else:
        # Local development
        return f"http://localhost:{PREVIEW_PORT}"


PREVIEW_URL = os.getenv("PREVIEW_URL", get_preview_url())


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
    # In HF Spaces, preview app runs as separate service, no need to manage subprocess
    if os.getenv("SPACE_ID") or os.getenv("HF_SPACE"):
        return

    global preview_process
    if preview_process and preview_process.poll() is None:
        print("🛑 Stopping preview app...")
        try:
            # Send SIGTERM to gracefully shutdown
            preview_process.terminate()
            # Wait a bit for graceful shutdown
            preview_process.wait(timeout=5)
            print("✅ Preview app stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown fails
            preview_process.kill()
            print("⚠️ Preview app force-killed after timeout")
        except Exception as e:
            print(f"❌ Error stopping preview app: {e}")
        finally:
            preview_process = None
    else:
        if preview_process is None:
            print("ℹ️ No preview app process to stop")
        else:
            print("ℹ️ Preview app process already terminated")


def start_preview_app():
    """Start the preview app in a subprocess."""
    # In HF Spaces, preview app runs as separate service via supervisor
    if os.getenv("SPACE_ID") or os.getenv("HF_SPACE"):
        print("✅ Preview app managed by supervisor in HF Spaces")
        return True, "Preview app running via supervisor"

    global preview_process

    # Stop any existing preview app
    stop_preview_app()

    app_path = find_app_py_in_sandbox()

    if not app_path or not os.path.exists(app_path):
        error_msg = "No app.py found in sandbox directory or its subfolders"
        print(f"❌ Preview Error: {error_msg}")
        return False, error_msg

    try:
        print(f"🚀 Starting preview app from: {app_path}")
        # Start the subprocess to run the sandbox app
        preview_process = subprocess.Popen(
            [
                sys.executable,
                app_path,
                "--server-port",
                str(PREVIEW_PORT),
                "--server-name",
                "0.0.0.0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait a moment for the server to start
        time.sleep(2)

        # Check if the process is still running
        if preview_process.poll() is not None:
            # Process has terminated, read the error
            stdout, stderr = preview_process.communicate()
            error_msg = f"App failed to start:\n{stderr}\n{stdout}"
            print(f"❌ Preview Error: {error_msg}")
            return False, error_msg

        # Try to verify the server is responding
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"http://localhost:{PREVIEW_PORT}", timeout=1)
                if response.status_code == 200:
                    print(
                        f"✅ Preview app started successfully on \
localhost:{PREVIEW_PORT}"
                    )
                    return True, "App started successfully"
            except requests.exceptions.RequestException:
                print(
                    f"🔄 Attempt {i+1}/{max_retries}: Waiting for server to respond..."
                )
                pass
            time.sleep(0.5)

        print(
            f"⚠️ Preview app started but may not be fully ready. \
            Check localhost:{PREVIEW_PORT}"
        )
        return True, "App started successfully"

    except Exception as e:
        error_msg = f"Error starting app: {str(e)}"
        print(f"❌ Preview Error: {error_msg}")
        return False, error_msg


def create_iframe_preview():
    """Create a simple iframe for the preview."""
    print("🔄 Creating iframe preview...")
    # Start the preview app
    success, message = start_preview_app()

    if not success:
        print(f"❌ Failed to create preview iframe: {message}")
        return f'<div style="padding: 20px; color: red;">\
            ❌ Failed to start preview: {message}\
            </div>'

    print("✅ Simple iframe preview created")
    return f'<iframe src="{PREVIEW_URL}" width="100%" height="600px" frameborder="0">\
</iframe>'


def is_preview_running():
    """Check if the preview app is running and accessible."""
    # In HF Spaces, assume preview app is always running via supervisor
    if os.getenv("SPACE_ID") or os.getenv("HF_SPACE"):
        return True

    global preview_process
    if preview_process is None or preview_process.poll() is not None:
        return False

    try:
        response = requests.get(f"http://localhost:{PREVIEW_PORT}", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def ensure_preview_running():
    """Ensure the preview app is running, start it if needed."""
    if not is_preview_running():
        print("Preview app not running, starting...")
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
                    chatbot = gr.Chatbot(
                        avatar_images=(
                            None,
                            "http://em-content.zobj.net/source/apple/419/growing-heart_1f497.png",
                        ),
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
                        preview_html = gr.HTML(
                            value=create_iframe_preview(), elem_id="preview-container"
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

            def save_and_refresh(path, new_text):
                save_file(path, new_text)
                # Wait a moment for file to be saved
                time.sleep(0.5)
                # Return updated iframe preview with forced refresh
                return create_iframe_preview()

            def refresh_all():
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

                preview_html = create_iframe_preview()

                return file_explorer, code_editor, preview_html

            save_btn.click(
                fn=save_and_refresh,
                inputs=[file_explorer, code_editor],
                outputs=[preview_html],
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
                fn=refresh_all,
                inputs=[],
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
                fn=refresh_all,
                inputs=[],
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

            def on_app_load():
                ensure_preview_running()
                return create_iframe_preview()

            demo.load(fn=on_app_load, outputs=[preview_html])

            # Clean up on app close
            def cleanup():
                stop_preview_app()

            demo.unload(cleanup)

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
    from kiss_agent import KISSAgent

    agent = KISSAgent()

    # Determine port based on environment
    if os.getenv("SPACE_ID") or os.getenv("HF_SPACE"):
        # In HF Spaces, run on 7862 (nginx will proxy to 7860)
        port = 7862
    else:
        # Local development
        port = 7860

    GradioUI(agent).launch(share=False, server_name="0.0.0.0", server_port=port)
