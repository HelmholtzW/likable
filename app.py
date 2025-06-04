import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import gradio as gr
import requests

from manager_agent import GradioManagerAgent
from utils import load_file

gr.NO_RELOAD = False

# Global variables for managing the preview app subprocess
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


def generate_ai_response(message, history):
    """Generate AI response using the manager agent for planning and \
coding agent for implementation."""

    history.append({"role": "user", "content": message})
    manager_agent_instance = GradioManagerAgent()

    if manager_agent_instance is None:
        # Fallback to mock response if planning agent fails to initialize
        response = (
            "Sorry, the manager agent is not available. "
            "Please check your API_KEY environment variable."
        )
        history.append({"role": "assistant", "content": response})
        return history, ""

    try:
        manager_result = manager_agent_instance(message)
        history.append({"role": "assistant", "content": manager_result})

    except Exception as e:
        error_response = f"I encountered an error: {str(e)}"
        history.append({"role": "assistant", "content": error_response})

    return history, ""


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
    app_path = find_app_py_in_sandbox()

    if not app_path or not os.path.exists(app_path):
        return """
        <div style='padding: 20px; text-align: center; color: #666;'>
            <h3>❌ No app.py found</h3>
            <p>Create an app.py file in the sandbox directory to see the preview.</p>
        </div>
        """

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


# Create the main Likable UI
def create_likable_ui():
    with gr.Blocks(
        title="💗Likable",
        theme=gr.themes.Soft(),
        fill_height=True,
        fill_width=True,
    ) as demo:
        gr.Markdown("# 💗Likable")
        gr.Markdown(
            "*AI-powered Gradio app builder - Plans and implements \
complete applications*"
        )

        with gr.Row(elem_classes="main-container"):
            # Left side - Chat Interface
            with gr.Column(scale=1, elem_classes="chat-container"):
                chatbot = gr.Chatbot(
                    show_copy_button=True,
                    avatar_images=(None, "💗"),
                    type="messages",
                    height="75vh",
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Describe the Gradio app you want to build...",
                        scale=4,
                        container=False,
                    )
                    send_btn = gr.Button("Build App", scale=1, variant="primary")

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

                        # Get initial code content dynamically
                        def get_initial_code():
                            app_path = find_app_py_in_sandbox()
                            if app_path and os.path.exists(app_path):
                                return load_file(app_path)
                            return "# No app created yet - use the chat to create one!"

                        code_editor = gr.Code(
                            scale=3,
                            value=get_initial_code(),
                            language="python",
                            visible=True,
                            interactive=True,
                            autocomplete=True,
                        )

        # Event handlers
        file_explorer.change(fn=load_file, inputs=file_explorer, outputs=code_editor)

        def save_and_refresh(path, new_text):
            save_file(path, new_text)
            # Wait a moment for file to be saved
            time.sleep(0.5)
            # Return updated iframe preview with forced refresh
            return create_iframe_preview()

        save_btn.click(
            fn=save_and_refresh,
            inputs=[file_explorer, code_editor],
            outputs=[preview_html],
        )

        # Event handlers for chat - updated to use the combined planning and
        # coding function
        msg_input.submit(
            generate_ai_response,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

        send_btn.click(
            generate_ai_response,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

        # Auto-start preview when the app loads
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
    # Register cleanup function to run on exit
    atexit.register(stop_preview_app)

    demo = create_likable_ui()
    # gradio_config = settings.get_gradio_config()

    # Ensure cleanup on exit
    def signal_handler(signum, frame):
        stop_preview_app()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        demo.launch(server_name="0.0.0.0", server_port=7862)
    finally:
        stop_preview_app()
