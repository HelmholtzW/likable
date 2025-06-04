import os
import subprocess
from pathlib import Path

from smolagents import LiteLLMModel, MCPClient, ToolCallingAgent, tool

from src.settings import settings

PROMPT_TEMPLATE = """You are an expert software developer for Gradio.
You are given a task to develop a Gradio application and can use all the tools at your disposal to do so.
You always try to do everything inside of the app.py file. Only in rare cases you might need to edit or create other files.

The overarching goal is always to create a Gradio application.

Here is the user's request:
{task}

Always test the app.py file after you have made changes to it!
"""


@tool
def python_editor(whole_edit: str) -> str:
    """
    Edit python files using aider's whole edit format. You can use this tool to edit any python file or create a new one.

    Your input should be a string in the following format:
    [filename]
    ```python
    [complete file content]
    ```

    For example:
    app.py
    ```python
    import gradio as gr
    ...
    ```

    Args:
        whole_edit: The new complete content in whole edit format

    Returns:
        Status message indicating success or failure
    """
    try:
        # Split into lines and find first non-empty line as filename
        lines = whole_edit.strip().split("\n")
        if not lines:
            return "Error: Empty input provided"

        filename = next((line.strip() for line in lines if line.strip()), None)
        if not filename:
            return "Error: No filename found in input"

        # Find code block content between ```
        content = whole_edit.strip()
        start_marker = content.find("```")
        if start_marker == -1:
            return "Error: No code block found"

        # Find the end of the first line after ```
        start_content = content.find("\n", start_marker) + 1
        end_marker = content.find("```", start_content)

        if end_marker == -1:
            # No closing ```, take everything after the opening ```
            file_content = content[start_content:]
        else:
            file_content = content[start_content:end_marker]

        # Create the file path and write content
        file_path = Path("./sandbox") / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content.rstrip())  # Remove trailing whitespace

        line_count = (
            len(file_content.strip().split("\n")) if file_content.strip() else 0
        )
        return f"Successfully wrote {line_count} lines to {filename}"

    except Exception as e:
        return f"Error applying whole edit: {str(e)}"


@tool
def test_app_py() -> str:
    """
    Test if the current app.py runs without syntax errors.

    Returns:
        Test result message
    """
    try:
        app_path = Path("sandbox") / "app.py"

        if not app_path.exists():
            return "Error: app.py does not exist"

        # Store original working directory
        original_cwd = os.getcwd()

        # Change to project directory for testing
        os.chdir(app_path.parent)

        # Test syntax by attempting to compile
        result = subprocess.run(
            ["python", "-m", "py_compile", "app.py"],
            capture_output=True,
            text=True,
        )

        # Change back to original directory
        os.chdir(original_cwd)

        if result.returncode == 0:
            return "✅ app.py syntax check passed successfully"
        else:
            return f"❌ Syntax error in app.py:\n{result.stderr}"

    except Exception as e:
        # Restore working directory on error
        try:
            os.chdir(original_cwd)
        except NameError:
            pass
        return f"Error testing app.py: {str(e)}"


class KISSAgent(ToolCallingAgent):
    def __init__(
        self,
        model_id: str | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
        prompt_template: str | None = None,
        **kwargs,
    ):
        model_id = model_id or settings.manager_model_id
        api_base_url = api_base_url or settings.api_base_url
        api_key = api_key or settings.api_key
        self.prompt_template = prompt_template or PROMPT_TEMPLATE

        # Initialize the language model
        model = LiteLLMModel(
            model_id=model_id,
            api_base=api_base_url,
            api_key=api_key,
        )

        # Initialize the parent CodeAgent
        super().__init__(
            tools=[python_editor, test_app_py],
            model=model,
            add_base_tools=False,
            **kwargs,
        )

    def run(self, task: str, **kwargs) -> str:
        """Override run method to format prompt with task before calling parent run."""
        formatted_prompt = self.prompt_template.format(task=task)
        return super().run(formatted_prompt, **kwargs)
