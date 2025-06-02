import random
import time

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


# Mock functions for preview and code
def get_preview_content():
    """Return HTML content for preview"""
    return """
    <div style="padding: 20px; font-family: Arial, sans-serif;">
        <h2>Preview - Generated App</h2>
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0;
                    border-radius: 8px;">
            <h3>Todo App</h3>
            <input type="text" placeholder="Add a new task..."
                   style="width: 70%; padding: 8px; margin-right: 10px;">
            <button style="padding: 8px 15px; background: #007bff; color: white;
                           border: none; border-radius: 4px;">Add</button>
            <ul style="margin-top: 15px; list-style-type: none; padding: 0;">
                <li style="padding: 8px; border-bottom: 1px solid #eee;">
                    ✓ Learn Gradio</li>
                <li style="padding: 8px; border-bottom: 1px solid #eee;">
                    ✓ Build awesome UIs</li>
                <li style="padding: 8px; border-bottom: 1px solid #eee;">
                    ⬜ Deploy to HuggingFace</li>
            </ul>
        </div>
        <p style="color: #666; font-size: 14px;">
            This is a live preview of your generated application.</p>
    </div>
    """


def get_code_content():
    """Return code content for the code view"""
    return """import gradio as gr

def add_task(new_task, tasks):
    if new_task.strip():
        tasks.append(new_task)
    return "", tasks

def create_todo_app():
    with gr.Blocks() as app:
        gr.Markdown("# Todo App")

        with gr.Row():
            new_task = gr.Textbox(
                placeholder="Add a new task...",
                scale=3,
                container=False
            )
            add_btn = gr.Button("Add", scale=1)

        task_list = gr.Dataframe(
            headers=["Tasks"],
            datatype=["str"],
            interactive=False
        )

        add_btn.click(
            add_task,
            inputs=[new_task, task_list],
            outputs=[new_task, task_list]
        )

        new_task.submit(
            add_task,
            inputs=[new_task, task_list],
            outputs=[new_task, task_list]
        )

    return app

if __name__ == "__main__":
    demo = create_todo_app()
    demo.launch()"""


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
        gr.Info(f"✅ Saved to: {path}")
    except Exception as e:
        gr.Error(f"❌ Error saving: {e}")


# Create the main Lovable-style UI
def create_lovable_ui():
    with gr.Blocks(
        title="💗Likable",
        theme=gr.themes.Soft(),
        fill_height=True,
    ) as demo:
        gr.Markdown("# 💗Likable")
        gr.Markdown(
            "*It's almost Lovable - Build Gradio apps using only a chat interface*"
        )

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
                    preview = gr.HTML(value=get_preview_content(), visible=True)

                with gr.Tab("Code"):
                    with gr.Row():
                        save_btn = gr.Button("Save", size="sm")
                    with gr.Row(equal_height=True):
                        file_explorer = gr.FileExplorer(
                            scale=1, file_count="single", value="app.py"
                        )
                        code_editor = gr.Code(
                            scale=3,
                            value=load_file("app.py"),
                            language="python",
                            visible=True,
                            interactive=True,
                        )

        file_explorer.change(fn=load_file, inputs=file_explorer, outputs=code_editor)
        save_btn.click(
            fn=save_file,
            inputs=[file_explorer, code_editor],
            outputs=[],
        )

        # Event handlers
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
