import importlib.util
import os
import sys
import subprocess
import time
import signal
import threading
import requests
import atexit

import gradio as gr

from planning_agent import GradioPlanningAgent
from settings import settings

gr.NO_RELOAD = False

# Initialize the planning agent globally
planning_agent = None

# Global variables for managing the preview app subprocess
preview_process = None
PREVIEW_PORT = 7861  # Different port from main app
PREVIEW_URL = f"http://localhost:{PREVIEW_PORT}"


def get_planning_agent():
    """Get or initialize the planning agent (lazy loading)."""
    global planning_agent
    if planning_agent is None:
        try:
            planning_agent = GradioPlanningAgent()
        except Exception as e:
            print(f"Error initializing planning agent: {e}")
            return None
    return planning_agent


# Enhanced AI response using the planning agent
def ai_response_with_planning(message, history):
    """Generate AI response using the planning agent for actual planning."""

    agent = get_planning_agent()

    if agent is None:
        # Fallback to mock response if agent fails to initialize
        response = (
            "Sorry, the planning agent is not available. "
            "Please check your API_KEY environment variable."
        )
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        return history, ""

    try:
        # Use the planning agent for actual planning
        planning_result = agent.plan_application(message)

        # Format the response with key insights
        action_summary = (
            planning_result.action_plan[:300] + "..."
            if len(planning_result.action_plan) > 300
            else planning_result.action_plan
        )

        components_list = chr(10).join(
            [f"• {comp}" for comp in planning_result.gradio_components[:5]]
        )
        dependencies_list = chr(10).join(
            [f"• {dep}" for dep in planning_result.dependencies[:5]]
        )

        response = f"""I'll help you plan that application! Here's what I've analyzed:

**Complexity**: {planning_result.estimated_complexity}

**Key Gradio Components Needed**:
{components_list}

**Dependencies Required**:
{dependencies_list}

**High-Level Action Plan**:
{action_summary}

I've created a comprehensive plan including implementation details and testing \
strategy. Check the detailed view for the complete plan!"""

        # Store the full planning result for later use
        # You could save this to a session state or database

    except Exception as e:
        response = (
            f"I encountered an error while planning: {str(e)}. "
            "Let me try a simpler approach..."
        )

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    return history, ""


def load_file(path):
    if path is None:
        return ""
    # path is a string like "subdir/example.py"
    with open(path, encoding="utf-8") as f:
        return f.read()


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

    app_path = "sandbox/app.py"

    if not os.path.exists(app_path):
        return False, "No app.py found in sandbox directory"

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
        for i in range(max_retries):
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
    app_path = "sandbox/app.py"

    if not os.path.exists(app_path):
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
            <pre style='background: #f5f5f5; padding: 10px; border-radius: 4px; text-align: left;'>{message}</pre>
        </div>
        """

    # Add timestamp to force iframe refresh
    timestamp = int(time.time() * 1000)
    preview_url_with_timestamp = f"{PREVIEW_URL}?t={timestamp}"

    return f"""
    <div style='width: 100%; height: 70vh; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;'>
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


# Create the main Lovable-style UI
def create_lovable_ui():
    with gr.Blocks(
        title="💗Likable",
        theme=gr.themes.Soft(),
        fill_height=True,
        fill_width=True,
    ) as demo:
        gr.Markdown("# 💗Likable")
        # gr.Markdown(
        #     "*It's almost Lovable - Build Gradio apps using only a chat interface*"
        # )

        with gr.Row(elem_classes="main-container"):
            # Left side - Chat Interface
            with gr.Column(scale=1, elem_classes="chat-container"):
                chatbot = gr.Chatbot(
                    show_copy_button=True,
                    avatar_images=(None, "💗"),
                    bubble_full_width=False,
                    height="75vh",
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Describe what you want to build...",
                        scale=4,
                        container=False,
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary")

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
                            # lines=27,
                            # max_lines=27,
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

        # Event handlers for chat
        msg_input.submit(
            ai_response_with_planning,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

        send_btn.click(
            ai_response_with_planning,
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

    demo = create_lovable_ui()
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
