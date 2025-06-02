import random
import time
import os
import sys
import importlib.util
import gradio as gr


# Mock function to simulate AI responses
def simulate_ai_response(message, history):
    """Simulate an AI response for demonstration purposes"""
    time.sleep(1)  # Simulate processing time

    # Simple demo responses
    responses = [
        "I'll help you build that! Let me generate some code for you.",
        "Great idea! I'm working on implementing that feature.",
        "Here's what I can create for you based on your request.",
        "Let me design that component and show you a preview.",
        "I understand what you need. I'll code that up right now!",
    ]

    response = random.choice(responses)
    history.append([message, response])
    return history, ""


def load_file(path):
    if path is None:
        return ""
    # path is a string like "subdir/example.py"
    with open(path, "r", encoding="utf-8") as f:
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


def load_and_render_app():
    """Load and render the Gradio app from sandbox/app.py"""
    app_path = "sandbox/app.py"

    if not os.path.exists(app_path):
        return gr.HTML(
            "<div style='padding: 20px; color: red;'>❌ No app.py found in sandbox directory</div>"
        )

    try:
        # Read the app code
        with open(app_path, "r", encoding="utf-8") as f:
            app_code = f.read()

        # Create a temporary module
        spec = importlib.util.spec_from_loader("dynamic_app", loader=None)
        module = importlib.util.module_from_spec(spec)

        # Add current directory to sys.path if not already there
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

        # Execute the code in the module's namespace
        exec(app_code, module.__dict__)

        # Look for common app creation patterns
        app_instance = None

        # Try to find the app instance
        if hasattr(module, "demo"):
            app_instance = module.demo
        elif hasattr(module, "app"):
            app_instance = module.app
        elif hasattr(module, "interface"):
            app_instance = module.interface
        else:
            # Look for any Gradio Blocks or Interface objects
            for name, obj in module.__dict__.items():
                if isinstance(obj, (gr.Blocks, gr.Interface)):
                    app_instance = obj
                    break

        if app_instance is None:
            return gr.HTML(
                "<div style='padding: 20px; color: orange;'>⚠️ No Gradio app found. Make sure your app.py creates a Gradio Blocks or Interface object.</div>"
            )

        # Return the app instance to be rendered
        return app_instance

    except Exception as e:
        error_html = f"""
        <div style='padding: 20px; color: red; font-family: monospace;'>
            ❌ Error loading app:<br>
            <pre style='background: #f5f5f5; padding: 10px; margin-top: 10px; border-radius: 4px;'>{str(e)}</pre>
        </div>
        """
        return gr.HTML(error_html)


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
                    height=500,
                    show_copy_button=True,
                    avatar_images=(None, "🤖"),
                    bubble_full_width=False,
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
                    # Create a trigger for refreshing the preview
                    refresh_trigger = gr.State(value=0)

                    # Use gr.render for dynamic app rendering
                    @gr.render(inputs=refresh_trigger)
                    def render_preview(trigger_value):
                        return load_and_render_app()

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
                            lines=28,
                            max_lines=28,
                            autocomplete=True,
                        )

        # Event handlers
        file_explorer.change(fn=load_file, inputs=file_explorer, outputs=code_editor)

        def save_and_refresh(path, new_text, current_trigger):
            save_file(path, new_text)
            # Increment trigger to refresh the preview
            return current_trigger + 1

        save_btn.click(
            fn=save_and_refresh,
            inputs=[file_explorer, code_editor, refresh_trigger],
            outputs=[refresh_trigger],
        )

        # Event handlers for chat
        msg_input.submit(
            simulate_ai_response,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

        send_btn.click(
            simulate_ai_response,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

    return demo


if __name__ == "__main__":
    demo = create_lovable_ui()
    demo.launch(debug=True)
