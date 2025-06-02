import gradio as gr
import time
import random


gr.NO_RELOAD = False


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
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px;">
            <h3>Todo App</h3>
            <input type="text" placeholder="Add a new task..." style="width: 70%; padding: 8px; margin-right: 10px;">
            <button style="padding: 8px 15px; background: #007bff; color: white; border: none; border-radius: 4px;">Add</button>
            <ul style="margin-top: 15px; list-style-type: none; padding: 0;">
                <li style="padding: 8px; border-bottom: 1px solid #eee;">✓ Learn Gradio</li>
                <li style="padding: 8px; border-bottom: 1px solid #eee;">✓ Build awesome UIs</li>
                <li style="padding: 8px; border-bottom: 1px solid #eee;">⬜ Deploy to HuggingFace</li>
            </ul>
        </div>
        <p style="color: #666; font-size: 14px;">This is a live preview of your generated application.</p>
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


# Create the main Lovable-style UI
def create_lovable_ui():
    with gr.Blocks(
        title="💗Likable",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown("# 💗Likable")
        # gr.Markdown(
        #     "*It's almost Lovable - Build Gradio apps using only a chat interface*"
        # )

        with gr.Tabs():
            # Preview Tab
            with gr.TabItem("Preview"):
                with gr.Row(elem_classes="main-container", equal_height=True):
                    # Left side - Chat Interface
                    with gr.Column(scale=1, elem_classes="chat-container"):
                        chatbot_preview = gr.Chatbot(
                            height=500,
                            show_copy_button=True,
                            avatar_images=(None, "🤖"),
                            bubble_full_width=False,
                        )

                        with gr.Row():
                            msg_input_preview = gr.Textbox(
                                placeholder="Describe what you want to build...",
                                scale=4,
                                container=False,
                            )
                            send_btn_preview = gr.Button(
                                "Send", scale=1, variant="primary"
                            )

                    # Right side - Preview Content
                    with gr.Column(scale=4, elem_classes="content-container"):
                        # with gr.Row():
                        #     gr.Button(
                        #         "Deploy to HF Spaces", variant="secondary", scale=1
                        #     )

                        preview_html = gr.HTML(value=get_preview_content())

            # Code Tab
            with gr.TabItem("Code"):
                with gr.Row(elem_classes="main-container", equal_height=True):
                    # Left side - Chat Interface
                    with gr.Column(scale=1, elem_classes="chat-container"):
                        chatbot_code = gr.Chatbot(
                            height=500,
                            show_copy_button=True,
                            avatar_images=(None, "🤖"),
                            bubble_full_width=False,
                        )

                        with gr.Row():
                            msg_input_code = gr.Textbox(
                                placeholder="Describe what you want to build...",
                                scale=4,
                                container=False,
                            )
                            send_btn_code = gr.Button(
                                "Send", scale=1, variant="primary"
                            )

                    # Right side - Code Content
                    with gr.Column(scale=4, elem_classes="content-container"):
                        # with gr.Row():
                        #     gr.Button(
                        #         "Deploy to HF Spaces", variant="secondary", scale=1
                        #     )

                        code_view = gr.Code(
                            value=get_code_content(),
                            language="python",
                            lines=20,
                            wrap_lines=True,
                            show_label=False,
                        )

        # Event handlers for Preview tab
        msg_input_preview.submit(
            simulate_ai_response,
            inputs=[msg_input_preview, chatbot_preview],
            outputs=[chatbot_preview, msg_input_preview],
        )

        send_btn_preview.click(
            simulate_ai_response,
            inputs=[msg_input_preview, chatbot_preview],
            outputs=[chatbot_preview, msg_input_preview],
        )

        # Event handlers for Code tab
        msg_input_code.submit(
            simulate_ai_response,
            inputs=[msg_input_code, chatbot_code],
            outputs=[chatbot_code, msg_input_code],
        )

        send_btn_code.click(
            simulate_ai_response,
            inputs=[msg_input_code, chatbot_code],
            outputs=[chatbot_code, msg_input_code],
        )

    return demo


if __name__ == "__main__":
    demo = create_lovable_ui()
    demo.launch(debug=True)
