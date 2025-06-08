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
PREVIEW_URL = f"http://localhost:{PREVIEW_PORT}"


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
                "127.0.0.1",
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
                response = requests.get(PREVIEW_URL, timeout=1)
                if response.status_code == 200:
                    print(f"✅ Preview app started successfully on {PREVIEW_URL}")
                    return True, "App started successfully"
            except requests.exceptions.RequestException:
                print(
                    f"🔄 Attempt {i+1}/{max_retries}: Waiting for server to respond..."
                )
                pass
            time.sleep(0.5)

        print(f"⚠️ Preview app started but may not be fully ready. Check {PREVIEW_URL}")
        return True, "App started successfully"

    except Exception as e:
        error_msg = f"Error starting app: {str(e)}"
        print(f"❌ Preview Error: {error_msg}")
        return False, error_msg


def create_iframe_preview():
    """Create an iframe HTML element for the preview."""
    print("🔄 Creating iframe preview...")
    # Start the preview app
    success, message = start_preview_app()

    if not success:
        print(f"❌ Failed to create preview iframe: {message}")
        return f"""
        <div style='padding: 20px; text-align: center; color: #d32f2f;'>
            <h3>❌ Failed to start preview</h3>
            <pre style='background: #f5f5f5; padding: 10px; \
border-radius: 4px; text-align: left;'>{message}</pre>
        </div>
        """

    # Add timestamp to force iframe refresh
    timestamp = int(time.time() * 1000)
    print("✅ Iframe preview created successfully")

    return f"""
    <div style='width: 100%; height: 70vh; border: 1px solid #ddd; border-radius: \
    8px; overflow: hidden; position: relative; background: #f9f9f9;'>
        <iframe
            id="preview-iframe-{timestamp}"
            src="{PREVIEW_URL}"
            width="100%"
            height="100%"
            frameborder="0"
            style="border: none; background: white;"
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups \
            allow-top-navigation allow-modals"
            loading="eager"
            onload="document.getElementById('loading-{timestamp}').style.display='none'"
            onerror="document.getElementById('iframe-{timestamp}').style.display='none';\
             document.getElementById('fallback-{timestamp}').style.display='block'"
        ></iframe>

        <!-- Loading indicator -->
        <div id="loading-{timestamp}" style="position: absolute; top: 0; left: 0; \
            width: 100%; height: 100%; background: rgba(255,255,255,0.9); \
            display: flex; align-items: center; justify-content: center; z-index: 10;">
            <div style="text-align: center;">
                <div style="border: 4px solid #f3f3f3; border-top: 4px solid #007bff; \
                border-radius: 50%; width: 40px; height: 40px; animation: spin 1s \
                linear infinite; margin: 0 auto 15px;"></div>
                <p style="color: #666; margin: 0;">Loading preview...</p>
            </div>
        </div>

        <!-- Fallback content -->
        <div id="fallback-{timestamp}" style="display: none; padding: 20px; \
            text-align: center; height: 100%; display: flex; flex-direction: column; \
            justify-content: center;">
            <div style='background: white; border-radius: 8px; padding: 30px; \
                margin: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);'>
                <h3 style='color: #28a745; margin-bottom: 20px;'>
                    🚀 Preview App Running!
                </h3>
                <p style='color: #666; margin-bottom: 25px; font-size: 16px;'>
                    Your Gradio app is running successfully.
                </p>
                <div style='margin: 20px 0;'>
                    <a href="{PREVIEW_URL}" target="_blank"
                       style='display: inline-block; padding: 12px 25px; background: \
                        #007bff; color: white;
                              text-decoration: none; border-radius: 6px; \
                                font-weight: bold; font-size: 16px;
                              box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                        🔗 Open Preview in New Tab
                    </a>
                </div>
                <div style='margin-top: 20px; padding: 15px; background: #f8f9fa; \
                border-radius: 4px; border-left: 4px solid #007bff;'>
                    <p style='margin: 0; color: #495057; font-size: 14px;'>
                        <strong>URL:</strong> <code style='background: #e9ecef; \
                        padding: 2px 6px; border-radius: 3px;'>{PREVIEW_URL}</code>
                    </p>
                </div>
            </div>
        </div>

        <!-- Open in new tab button -->
        <div style='position: absolute; top: 10px; right: 10px; z-index: 20;'>
            <a href="{PREVIEW_URL}" target="_blank"
               style='display: inline-block; padding: 8px 12px; background: \
                rgba(0,0,0,0.8); color: white;
                      text-decoration: none; border-radius: 4px; font-size: 12px;'>
                ↗ Open in new tab
            </a>
        </div>
    </div>

    <div style='padding: 10px; text-align: center; color: #666; font-size: 12px;'>
        Preview running on <a href="{PREVIEW_URL}" target="_blank">{PREVIEW_URL}</a>
        <span style='margin-left: 10px; color: #999;'>
            Last updated: {time.strftime('%H:%M:%S')}
        </span>
    </div>

    <style>
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    </style>

    <script>
    // Auto-fallback after 10 seconds if iframe doesn't load
    setTimeout(function() {{
        const loading = document.getElementById('loading-{timestamp}');
        const fallback = document.getElementById('fallback-{timestamp}');
        if (loading && loading.style.display !== 'none') {{
            loading.style.display = 'none';
            if (fallback) {{
                fallback.style.display = 'flex';
            }}
        }}
    }}, 10000);
    </script>
    """


def is_preview_running():
    """Check if the preview app is running and accessible."""
    global preview_process
    if preview_process is None or preview_process.poll() is not None:
        return False

    try:
        response = requests.get(PREVIEW_URL, timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def ensure_preview_running():
    """Ensure the preview app is running, start it if needed."""
    if not is_preview_running():
        print("Preview app not running, starting...")
        start_preview_app()


def save_api_key(provider, api_key):
    """Save API key to environment variable."""
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
        os.environ[env_var_name] = api_key.strip()
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
        status.append(f"✅ {selected_llm_provider}: {masked_key}")
    else:
        status.append(f"❌ {selected_llm_provider}: Not set")

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
                            lines=2,
                            max_lines=2,
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
                provider, api_key, selected_llm_provider="Anthropic"
            ):
                message = save_api_key(provider, api_key)
                status = get_api_key_status(selected_llm_provider)
                return message, status, ""  # Clear the input field

            hf_save_btn.click(
                lambda key, llm_prov: save_and_update_status(
                    "Hugging Face", key, llm_prov
                ),
                inputs=[hf_token, llm_provider],
                outputs=[api_message, api_status, hf_token],
            ).then(lambda: gr.Textbox(visible=True), outputs=[api_message])

            llm_save_btn.click(
                lambda provider, key: save_and_update_status(provider, key, provider),
                inputs=[llm_provider, llm_token],
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


if __name__ == "__main__":
    from kiss_agent import KISSAgent

    agent = KISSAgent()
    GradioUI(agent).launch(share=False, server_name="0.0.0.0", server_port=7860)
