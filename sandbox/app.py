import argparse
import json
from datetime import datetime

import gradio as gr


class TodoApp:
    def __init__(self):
        self.todos = []
        self.load_todos()

    def load_todos(self):
        """Load todos from a JSON file"""
        try:
            with open("todos.json") as f:
                self.todos = json.load(f)
        except FileNotFoundError:
            self.todos = []

    def save_todos(self):
        """Save todos to a JSON file"""
        with open("todos.json", "w") as f:
            json.dump(self.todos, f, indent=2)

    def add_todo(self, task: str) -> tuple[str, str]:
        """Add a new todo item"""
        if not task.strip():
            return self.get_todo_display(), "Please enter a task!"

        new_todo = {
            "id": len(self.todos) + 1,
            "task": task.strip(),
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.todos.append(new_todo)
        self.save_todos()
        return self.get_todo_display(), "Task added successfully!"

    def toggle_todo(self, todo_id: int) -> str:
        """Toggle completion status of a todo"""
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["completed"] = not todo["completed"]
                self.save_todos()
                break
        return self.get_todo_display()

    def delete_todo(self, todo_id: int) -> str:
        """Delete a todo item"""
        self.todos = [todo for todo in self.todos if todo["id"] != todo_id]
        self.save_todos()
        return self.get_todo_display()

    def get_todo_display(self) -> str:
        """Get formatted display of all todos"""
        if not self.todos:
            return "No todos yet! Add your first task above."

        display = []
        for todo in self.todos:
            status = "✅" if todo["completed"] else "⏳"
            task_style = "~~" if todo["completed"] else ""
            display.append(
                f"{status} {task_style}{todo['task']}{task_style} (ID: {todo['id']})"
            )

        return "\n".join(display)

    def get_todo_list_for_actions(self) -> list[str]:
        """Get list of todos for dropdown selection"""
        if not self.todos:
            return ["No todos available"]
        return [f"{todo['id']}: {todo['task']}" for todo in self.todos]

    def clear_completed(self) -> str:
        """Remove all completed todos"""
        self.todos = [todo for todo in self.todos if not todo["completed"]]
        self.save_todos()
        return self.get_todo_display()

    def get_stats(self) -> str:
        """Get todo statistics"""
        total = len(self.todos)
        completed = sum(1 for todo in self.todos if todo["completed"])
        pending = total - completed

        return (
            f"📊 **Stats:** Total: {total} | "
            f"Completed: {completed} | Pending: {pending}"
        )


# Initialize the todo app
todo_app = TodoApp()


# Gradio interface functions
def add_task(task_input):
    display, message = todo_app.add_todo(task_input)
    return (
        display,
        message,
        "",
        todo_app.get_todo_list_for_actions(),
        todo_app.get_stats(),
    )


def toggle_task(selected_todo):
    if selected_todo == "No todos available":
        return (
            todo_app.get_todo_display(),
            "No todos to toggle!",
            todo_app.get_todo_list_for_actions(),
            todo_app.get_stats(),
        )

    try:
        todo_id = int(selected_todo.split(":")[0])
        display = todo_app.toggle_todo(todo_id)
        return (
            display,
            "Task status toggled!",
            todo_app.get_todo_list_for_actions(),
            todo_app.get_stats(),
        )
    except (ValueError, IndexError):
        return (
            todo_app.get_todo_display(),
            "Invalid selection!",
            todo_app.get_todo_list_for_actions(),
            todo_app.get_stats(),
        )


def delete_task(selected_todo):
    if selected_todo == "No todos available":
        return (
            todo_app.get_todo_display(),
            "No todos to delete!",
            todo_app.get_todo_list_for_actions(),
            todo_app.get_stats(),
        )

    try:
        todo_id = int(selected_todo.split(":")[0])
        display = todo_app.delete_todo(todo_id)
        return (
            display,
            "Task deleted!",
            todo_app.get_todo_list_for_actions(),
            todo_app.get_stats(),
        )
    except (ValueError, IndexError):
        return (
            todo_app.get_todo_display(),
            "Invalid selection!",
            todo_app.get_todo_list_for_actions(),
            todo_app.get_stats(),
        )


def clear_completed_tasks():
    display = todo_app.clear_completed()
    return (
        display,
        "Completed tasks cleared!",
        todo_app.get_todo_list_for_actions(),
        todo_app.get_stats(),
    )


def refresh_display():
    return (
        todo_app.get_todo_display(),
        todo_app.get_todo_list_for_actions(),
        todo_app.get_stats(),
    )


# Create the Gradio interface
with gr.Blocks(title="Simple Todo App", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 📝 Simple Todo App")
    gr.Markdown("A clean and simple todo application to manage your tasks")

    # Stats display
    stats_display = gr.Markdown(todo_app.get_stats())

    with gr.Row():
        with gr.Column(scale=3):
            task_input = gr.Textbox(
                placeholder="Enter a new task...", label="New Task", show_label=False
            )
        with gr.Column(scale=1):
            add_btn = gr.Button("Add Task", variant="primary")

    # Status message
    status_msg = gr.Textbox(label="Status", interactive=False, show_label=False)

    # Todo display
    todo_display = gr.Textbox(
        value=todo_app.get_todo_display(),
        label="Your Tasks",
        lines=10,
        interactive=False,
    )

    # Task actions
    gr.Markdown("### Task Actions")
    with gr.Row():
        with gr.Column():
            todo_selector = gr.Dropdown(
                choices=todo_app.get_todo_list_for_actions(),
                label="Select Task",
                interactive=True,
            )
        with gr.Column():
            with gr.Row():
                toggle_btn = gr.Button("Toggle Complete", variant="secondary")
                delete_btn = gr.Button("Delete Task", variant="stop")

    # Bulk actions
    with gr.Row():
        clear_completed_btn = gr.Button("Clear Completed", variant="secondary")
        refresh_btn = gr.Button("Refresh", variant="secondary")

    # Event handlers
    add_btn.click(
        fn=add_task,
        inputs=[task_input],
        outputs=[todo_display, status_msg, task_input, todo_selector, stats_display],
    )

    task_input.submit(
        fn=add_task,
        inputs=[task_input],
        outputs=[todo_display, status_msg, task_input, todo_selector, stats_display],
    )

    toggle_btn.click(
        fn=toggle_task,
        inputs=[todo_selector],
        outputs=[todo_display, status_msg, todo_selector, stats_display],
    )

    delete_btn.click(
        fn=delete_task,
        inputs=[todo_selector],
        outputs=[todo_display, status_msg, todo_selector, stats_display],
    )

    clear_completed_btn.click(
        fn=clear_completed_tasks,
        inputs=[],
        outputs=[todo_display, status_msg, todo_selector, stats_display],
    )

    refresh_btn.click(
        fn=refresh_display,
        inputs=[],
        outputs=[todo_display, todo_selector, stats_display],
    )

# Launch the app
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Gradio Todo App")
    parser.add_argument(
        "--server-port", type=int, default=7860, help="Port to run the server on"
    )
    parser.add_argument(
        "--server-name", type=str, default="0.0.0.0", help="Server name to bind to"
    )
    args = parser.parse_args()

    demo.launch(server_name=args.server_name, server_port=args.server_port)
