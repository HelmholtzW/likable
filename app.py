import os
import subprocess
import sys
import time
from pathlib import Path

import gradio as gr
import requests
from smolagents.agents import MultiStepAgent
from ui_helpers import stream_to_gradio

# from src.manager_agent import GradioManagerAgent
from src.utils import load_file

preview_process = None
PREVIEW_PORT = 7860  # Different port from main app
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
        try:
            # Send SIGTERM to gracefully shutdown
            preview_process.terminate()
            # Wait a bit for graceful shutdown
            preview_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown fails
            preview_process.kill()
        except Exception as e:
            print(f"Error stopping preview app: {e}")
        finally:
            preview_process = None


def start_preview_app():
    """Start the preview app in a subprocess."""
    global preview_process

    # Stop any existing preview app
    stop_preview_app()

    app_path = find_app_py_in_sandbox()

    if not app_path or not os.path.exists(app_path):
        return False, "No app.py found in sandbox directory or its subfolders"

    try:
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
            return False, f"App failed to start:\n{stderr}\n{stdout}"

        # Try to verify the server is responding
        max_retries = 10
        for _ in range(max_retries):
            try:
                response = requests.get(PREVIEW_URL, timeout=1)
                if response.status_code == 200:
                    return True, "App started successfully"
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)

        return True, "App started successfully"

    except Exception as e:
        return False, f"Error starting app: {str(e)}"


def create_iframe_preview():
    """Create an iframe HTML element for the preview."""
    # Start the preview app
    success, message = start_preview_app()

    if not success:
        return f"""
        <div style='padding: 20px; text-align: center; color: #d32f2f;'>
            <h3>❌ Failed to start preview</h3>
            <pre style='background: #f5f5f5; padding: 10px; \
border-radius: 4px; text-align: left;'>{message}</pre>
        </div>
        """

    # Add timestamp to force iframe refresh
    timestamp = int(time.time() * 1000)
    preview_url_with_timestamp = f"{PREVIEW_URL}?t={timestamp}"

    return f"""
    <div style='width: 100%; height: 70vh; border: 1px solid #ddd; \
border-radius: 8px; overflow: hidden;'>
        <iframe
            src="{preview_url_with_timestamp}"
            width="100%"
            height="100%"
            frameborder="0"
            style="border: none;"
            key="{timestamp}"
        ></iframe>
    </div>
    <div style='padding: 10px; text-align: center; color: #666; font-size: 12px;'>
        Preview running on <a href="{PREVIEW_URL}" target="_blank">{PREVIEW_URL}</a>
    </div>
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


class GradioUI:
    """A one-line interface to launch your agent in Gradio"""

    def __init__(self, agent: MultiStepAgent):
        self.agent = agent
        self.parent_id = None

    def interact_with_agent(self, prompt, messages, session_state):
        import gradio as gr

        self.parent_id = int(time.time() * 1000)
        messages.append(
            gr.ChatMessage(
                role="assistant",
                content="",
                metadata={"id": self.parent_id, "title": "...", "status": "pending"},
            )
        )
        # Get the agent type from the template agent
        if "agent" not in session_state:
            session_state["agent"] = self.agent

        try:
            messages.append(
                gr.ChatMessage(role="user", content=prompt, metadata={"status": "done"})
            )
            yield messages

            for msg in stream_to_gradio(
                session_state["agent"],
                task=prompt,
                reset_agent_memory=False,
                parent_id=self.parent_id,
            ):
                if isinstance(msg, gr.ChatMessage):
                    # messages[-1].metadata["status"] = "done"
                    # TODO make it so that only the final answer is shown, rest in drop down
                    messages.append(msg)
                    messages[-1].metadata["status"] = "done"
                    if msg.content.startswith("**Final answer:**"):
                        # Set the parent message status to done when final answer is reached
                        for message in messages:
                            if (
                                isinstance(message, gr.ChatMessage)
                                and message.metadata.get("id") == self.parent_id
                            ):
                                message.metadata["status"] = "done"
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
            raise gr.Error(f"Error in interaction: {str(e)}")

    def log_user_message(self, text_input, file_uploads_log):
        import gradio as gr

        return (
            text_input
            + (
                f"\nYou have been provided with these files, which might be helpful or not: {file_uploads_log}"
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

                # Right side - Preview/Code Toggle
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
            # Add session state to store session-specific data
            session_state = gr.State({})
            stored_messages = gr.State([])
            file_uploads_log = gr.State([])

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
    from kiss_agent import KISSAgent, test_app_py

    # t = test_app_py()
    agent = KISSAgent()
    GradioUI(agent).launch(share=False, server_name="0.0.0.0", server_port=7862)
