import os
import re
import subprocess
from pathlib import Path

from smolagents import LiteLLMModel, ToolCallingAgent, tool

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
def create_new_file(whole_edit: str) -> str:
    """
    Create python files using aider's whole edit format. You can use this tool to overwrite any python file or create a new one.

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
def python_editor(diff_content: str, filename: str = "app.py") -> str:
    """
    This tool allows you to edit the code in a python file by applying a diff edit to app.py using aider's diff edit format.

    The input should be in the format:
    [filename]
    ```
    <<<<<<< SEARCH
    [text to search for]
    =======
    [text to replace with]
    >>>>>>> REPLACE
    ```

    For multiple changes in the same file, include multiple search/replace blocks:

    Example with multiple changes:
    app.py
    ```
    <<<<<<< SEARCH
    def old_function():
        return "old"
    =======
    def new_function():
        return "new and improved"
    >>>>>>> REPLACE

    <<<<<<< SEARCH
    title="Old Title"
    =======
    title="New Amazing Title"
    >>>>>>> REPLACE

    <<<<<<< SEARCH
    # TODO: Add error handling
    result = process_data()
    =======
    # Error handling implemented
    try:
        result = process_data()
    except Exception as e:
        result = f"Error: {e}"
    >>>>>>> REPLACE
    ```

    Important notes:
    - Each search block must contain EXACT text that exists in the file
    - Search text is case-sensitive and whitespace-sensitive
    - You can have as many search/replace blocks as needed
    - All changes are applied sequentially in the order they appear
    - If any search text is not found, the entire operation fails

    Args:
        diff_content: The diff content in aider's diff format
        filename: Name of the file to edit

    Returns:
        Status message indicating success or failure
    """
    try:
        app_path = Path("sandbox") / filename

        if not app_path.exists():
            return "Error: app.py does not exist. Use setup_project_structure first."

        # Read current content
        with open(app_path) as f:
            current_content = f.read()

        # Parse the diff format
        lines = diff_content.strip().split("\n")

        # Look for filename
        filename_found = False
        for i, line in enumerate(lines):
            if line.strip() == "app.py":
                filename_found = True
                lines = lines[i + 1 :]  # Remove filename line
                break

        if not filename_found:
            return "Error: Expected filename 'app.py' not found in diff format"

        # Remove code block markers if present
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        # Parse search/replace blocks
        content_lines = "\n".join(lines)

        # Find all search/replace blocks
        search_replace_pattern = (
            r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE"
        )
        matches = re.findall(search_replace_pattern, content_lines, re.DOTALL)

        if not matches:
            return "Error: No valid search/replace blocks found in diff format"

        # Apply each search/replace
        modified_content = current_content
        replacements_made = 0

        for search_text, replace_text in matches:
            # Clean up the search and replace text
            search_text = search_text.strip()
            replace_text = replace_text.strip()

            if search_text in modified_content:
                modified_content = modified_content.replace(search_text, replace_text)
                replacements_made += 1
            else:
                return f"Error: Search text not found in app.py:\n{search_text}"

        # Write the modified content back
        with open(app_path, "w") as f:
            f.write(modified_content)

        return f"Successfully applied {replacements_made} diff replacements to app.py"

    except Exception as e:
        return f"Error applying diff edit: {str(e)}"


@tool
def file_explorer() -> str:
    """This tool shows you the file structure of your working directory.

    Returns:
        str: file structure of your working directory
    """
    return "File structure of your working directory:\n" + "\n".join(
        [f"- {file}" for file in os.listdir("sandbox")]
    )


@tool
def file_viewer(filename: str) -> str:
    """This tool shows you the content of a file.

    Args:
        filename: Name of the file to view

    Returns:
        str: content of the file
    """
    with open(Path("sandbox") / filename, "r") as f:
        return f.read()


@tool
def test_app_py() -> str:
    """
    Test if the current app.py runs without syntax errors and starts successfully.
    For server applications like Gradio, this will start the server and then stop it.

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

        # Start the subprocess without waiting for completion
        process = subprocess.Popen(
            ["python", "app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for a short time to see if the process starts successfully
            # If it exits immediately with an error, we'll catch it
            stdout, stderr = process.communicate(timeout=5)

            # If we get here, the process exited within 10 seconds
            # Check for errors in stderr or stdout, not just return code
            error_indicators = [
                "error",
                "exception",
                "traceback",
                "attributeerror",
                "importerror",
                "modulenotfounderror",
            ]

            # Combine stdout and stderr for error checking
            all_output = (stdout or "") + (stderr or "")
            all_output_lower = all_output.lower()

            # Check if any error indicators are present
            has_error = any(
                indicator in all_output_lower for indicator in error_indicators
            )

            if process.returncode != 0 or has_error:
                error_output = stderr if stderr else stdout
                return f"❌ Error running app.py:\n{error_output}"
            else:
                return "✅ app.py executed successfully"

        except subprocess.TimeoutExpired:
            # Process is still running after 3 seconds - likely a server
            # This is actually good news for server apps like Gradio
            process.terminate()

            # Wait a bit for graceful termination
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                process.kill()
                process.wait()

            # Check if there were any immediate errors in stderr
            try:
                _, stderr = process.communicate(timeout=1)
                if stderr and "error" in stderr.lower():
                    return f"❌ Error detected in app.py:\n{stderr}"
            except:
                pass

            return "✅ app.py started successfully (server detected and stopped)"

    except Exception as e:
        return f"Error testing app.py: {str(e)}"
    finally:
        # Change back to original directory
        try:
            os.chdir(original_cwd)
        except NameError:
            pass


class KISSAgent(ToolCallingAgent):
    def __init__(
        self,
        model_id: str | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
        prompt_template: str | None = None,
        **kwargs,
    ):
        model_id = model_id or settings.model_id
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
            tools=[
                python_editor,
                test_app_py,
                file_explorer,
                file_viewer,
                create_new_file,
            ],
            model=model,
            add_base_tools=False,
            **kwargs,
        )
        # TODO: add callback to manage memory to limit context window

    def run(self, task: str, **kwargs) -> str:
        """Override run method to format prompt with task before calling parent run."""
        formatted_prompt = self.prompt_template.format(task=task)
        return super().run(formatted_prompt, **kwargs)
