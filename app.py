import importlib.util
import os
import sys

import gradio as gr

from coding_agent import GradioCodingAgent
from planning_agent import GradioPlanningAgent
from settings import settings
from utils import load_file

gr.NO_RELOAD = False

# Initialize the agents globally
planning_agent = None
coding_agent = None


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


def get_coding_agent():
    """Get or initialize the coding agent (lazy loading)."""
    global coding_agent
    if coding_agent is None:
        try:
            coding_agent = GradioCodingAgent()
        except Exception as e:
            print(f"Error initializing coding agent: {e}")
            return None
    return coding_agent


# Enhanced AI response using both planning and coding agents
def ai_response_with_planning_and_coding(message, history):
    """Generate AI response using the planning agent for planning and \
coding agent for implementation."""

    planning_agent_instance = get_planning_agent()
    coding_agent_instance = get_coding_agent()

    if planning_agent_instance is None:
        # Fallback to mock response if planning agent fails to initialize
        response = (
            "Sorry, the planning agent is not available. "
            "Please check your API_KEY environment variable."
        )
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        return history, ""

    if coding_agent_instance is None:
        # Fallback if coding agent fails to initialize
        response = (
            "Sorry, the coding agent is not available. "
            "Planning is available but implementation will be limited."
        )
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        return history, ""

    try:
        # Step 1: Use the planning agent for planning
        history.append({"role": "user", "content": message})
        history.append(
            {"role": "assistant", "content": "🎯 Starting to plan your application..."}
        )

        planning_result = planning_agent_instance.plan_application(message)

        # Format the planning response
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

        planning_response = f"""✅ **Planning Complete!**

**Complexity**: {planning_result.estimated_complexity}

**Key Gradio Components Needed**:
{components_list}

**Dependencies Required**:
{dependencies_list}

**High-Level Action Plan**:
{action_summary}

🚀 **Now starting implementation...**"""

        history.append({"role": "assistant", "content": planning_response})

        # Step 2: Use the coding agent for implementation
        history.append(
            {
                "role": "assistant",
                "content": "⚡ Implementing your application with proper \
project structure...",
            }
        )

        coding_result = coding_agent_instance.iterative_implementation(planning_result)

        # Format the implementation response
        if coding_result.success:
            implementation_response = f"""✅ **Implementation Complete!**

**Project Created**: `{coding_result.project_path}`
**Features Implemented**: {len(coding_result.implemented_features)} components
**Status**: Ready to run!

Your Gradio application has been created with:
- Proper `uv` project structure
- All required dependencies installed
- Complete README.md with usage instructions
- Functional app.py with all requested features

You can view and test your app in the **Preview** tab, or check the code in \
the **Code** tab.

To run locally: `cd {coding_result.project_path} && uv run python app.py`"""

            if coding_result.remaining_tasks:
                implementation_response += f"\n\n**Remaining Tasks**: \
{chr(10).join([f'• {task}' for task in coding_result.remaining_tasks])}"

        else:
            implementation_response = f"""⚠️ **Implementation Partially Complete**

**Project Path**: `{coding_result.project_path}`
**Issues Encountered**: {len(coding_result.error_messages)} errors

**Error Messages**:
{chr(10).join([f'• {error}' for error in coding_result.error_messages])}

**Remaining Tasks**:
{chr(10).join([f'• {task}' for task in coding_result.remaining_tasks])}

The project structure has been set up, but some features may need manual completion."""

        history.append({"role": "assistant", "content": implementation_response})

    except Exception as e:
        error_response = (
            f"I encountered an error during planning and implementation: {str(e)}. "
            "Let me try a simpler approach..."
        )
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


def load_and_render_app():
    """Load and render the Gradio app from sandbox/gradio_app/app.py"""
    app_path = "sandbox/gradio_app/app.py"

    if not os.path.exists(app_path):
        return gr.HTML(
            """<div style='padding: 20px; color: red;'>
    ❌ No app.py found in sandbox/gradio_app directory.
    Create an application first using the chat interface.
</div>"""
        )

    try:
        # Read the app code
        with open(app_path, encoding="utf-8") as f:
            app_code = f.read()

        # Create a temporary module
        spec = importlib.util.spec_from_loader("dynamic_app", loader=None)
        module = importlib.util.module_from_spec(spec)

        # Add sandbox directory to sys.path if not already there
        sandbox_path = os.path.abspath("sandbox/gradio_app")
        if sandbox_path not in sys.path:
            sys.path.insert(0, sandbox_path)

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
            for _, obj in module.__dict__.items():
                if isinstance(obj, gr.Blocks | gr.Interface):
                    app_instance = obj
                    break

        if app_instance is None:
            return gr.HTML(
                """<div style='padding: 20px; color: orange;'>
⚠️ No Gradio app found. Make sure your app.py creates a Gradio Blocks or \
Interface object.
</div>"""
            )

        # Return the app instance to be rendered
        return app_instance

    except Exception as e:
        error_html = f"""
<div style='padding: 20px; color: red; font-family: monospace;'>
    ❌ Error loading app:<br>
    <pre style='background: #f5f5f5; padding: 10px; margin-top: 10px; \
border-radius: 4px;'>{str(e)}</pre>
</div>
"""
        return gr.HTML(error_html)


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
                    avatar_images=(None, "🤖"),
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
                            value=load_file("sandbox/gradio_app/app.py")
                            if os.path.exists("sandbox/gradio_app/app.py")
                            else "# No app created yet - use the chat to create one!",
                            language="python",
                            visible=True,
                            interactive=True,
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

        # Event handlers for chat - updated to use the combined planning and
        # coding function
        msg_input.submit(
            ai_response_with_planning_and_coding,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

        send_btn.click(
            ai_response_with_planning_and_coding,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

    return demo


if __name__ == "__main__":
    demo = create_likable_ui()
    gradio_config = settings.get_gradio_config()
    demo.launch(**gradio_config)
