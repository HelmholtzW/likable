import gradio as gr

# Global list to store tasks
tasks = []


def add_task(task_text):
    """Add a new task to the list"""
    if task_text.strip():
        tasks.append({"text": task_text.strip(), "completed": False})
    return update_task_display(), ""


def toggle_task(task_index):
    """Toggle completion status of a task"""
    if 0 <= task_index < len(tasks):
        tasks[task_index]["completed"] = not tasks[task_index]["completed"]
    return update_task_display()


def delete_task(task_index):
    """Delete a task from the list"""
    if 0 <= task_index < len(tasks):
        tasks.pop(task_index)
    return update_task_display()


def update_task_display():
    """Update the task display"""
    if not tasks:
        return "No tasks yet!"

    display_text = ""
    for i, task in enumerate(tasks):
        status = "✓" if task["completed"] else "○"
        display_text += f"{i}: {status} {task['text']}\n"
    return display_text


# Create Gradio interface
with gr.Blocks(title="Simple To-Do List", theme=gr.themes.Monochrome()) as app:
    gr.Markdown("# Simple To-Do List")

    with gr.Row():
        task_input = gr.Textbox(
            placeholder="Enter a new task...", label="New Task", scale=3
        )
        add_btn = gr.Button("Add Task", scale=1)

    task_display = gr.Textbox(
        value="No tasks yet!", label="Tasks", lines=10, interactive=False
    )

    with gr.Row():
        task_index = gr.Number(label="Task Number", value=0, precision=0)
        toggle_btn = gr.Button("Toggle Complete")
        delete_btn = gr.Button("Delete Task")

    # Event handlers
    add_btn.click(add_task, inputs=[task_input], outputs=[task_display, task_input])

    task_input.submit(add_task, inputs=[task_input], outputs=[task_display, task_input])

    toggle_btn.click(toggle_task, inputs=[task_index], outputs=[task_display])

    delete_btn.click(delete_task, inputs=[task_index], outputs=[task_display])

if __name__ == "__main__":
    # Never change this port, otherwise the preview app will not work
    app.launch(server_name="0.0.0.0", server_port=7861)
