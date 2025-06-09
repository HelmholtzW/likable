import os
import re
import socket
import subprocess
from pathlib import Path

from smolagents import LiteLLMModel, ToolCallingAgent, tool

from src.settings import settings

PROMPT_TEMPLATE = """You are an expert software developer for Gradio.
You are given a task to develop a Gradio application and can use all the tools \
at your disposal to do so.
You always try to do everything inside of the app.py file. Only in rare cases \
you might need to edit or create other files.

The overarching goal is always to create a Gradio application.

**CRITICAL REQUIREMENT - ABSOLUTELY MANDATORY:**
Every app.py file you create MUST end with EXACTLY this code block:

```python
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
```

**THIS IS NOT OPTIONAL. THE APP WILL NOT WORK WITHOUT THIS EXACT CODE.**
**NEVER, UNDER ANY CIRCUMSTANCES, OMIT OR MODIFY THIS LAUNCH CODE.**
**IF YOU CREATE AN APP.PY WITHOUT THIS EXACT ENDING, THE APPLICATION WILL FAIL.**

Make sure to:
1. Import argparse at the top of the file
2. Name your Gradio interface `demo`
3. Include the EXACT launch code shown above at the very end
4. Adjust the description in argparse if needed for your specific app

Here is the user's request:
{task}

Always test the app.py file after you have made changes to it!
"""


@tool
def create_new_file(whole_edit: str) -> str:
    """
    Create python files using aider's whole edit format. You can use this tool
    to overwrite any python file or create a new one.

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
def install_package(package_name: str) -> str:
    """
    Install a Python package using uv when encountering ModuleNotFoundError.
    This tool adds the package to the project's dependencies and installs it.

    Args:
        package_name: Name of the package to install (e.g., 'requests', 'pandas==2.0.0')

    Returns:
        Status message indicating success or failure
    """
    try:
        # Store original working directory
        original_cwd = os.getcwd()

        # Change to the project root directory (where pyproject.toml is)
        os.chdir(Path(__file__).parent)

        # Run uv add command
        result = subprocess.run(
            ["uv", "add", package_name],
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout for package installation
        )

        if result.returncode == 0:
            return f"✅ Successfully installed {package_name} using uv"
        else:
            error_msg = result.stderr or result.stdout
            return f"❌ Failed to install {package_name}:\n{error_msg}"

    except subprocess.TimeoutExpired:
        return f"❌ Installation of {package_name} timed out after 60 seconds"
    except FileNotFoundError:
        return "❌ Error: uv command not found. Please make sure uv is installed."
    except Exception as e:
        return f"❌ Error installing {package_name}: {str(e)}"
    finally:
        # Change back to original directory
        try:
            os.chdir(original_cwd)
        except NameError:
            pass


def _find_free_port(start_port=7860, max_ports=100):
    """Find an available TCP port, starting from a given port."""
    for port in range(start_port, start_port + max_ports):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", port))
                return port
        except OSError:
            # This port is in use, try the next one
            continue
    return None


@tool
def python_editor(diff_content: str, filename: str = "app.py") -> str:
    """
    This tool allows you to edit the code in a python file by applying a diff
    edit to app.py using aider's diff edit format.

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
    with open(Path("sandbox") / filename) as f:
        return f.read()


@tool
def test_app_py() -> str:
    """
    Test the app.py file by running it as a subprocess.
    This test uses a hardcoded port (7865) to avoid conflicts.
    A successful test means the app launches and runs without crashing.
    """
    TEST_PORT = 7865
    try:
        app_path = Path("sandbox") / "app.py"
        if not app_path.exists():
            return "Error: app.py not found in sandbox directory."

        print(f"--- Starting test on port {TEST_PORT} ---")
        process = subprocess.Popen(
            ["python", str(app_path), "--server-port", str(TEST_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # The key is to see if the process crashes quickly.
        # If it runs for a few seconds, it's considered a success.
        try:
            # Wait for 5 seconds. If it exits, it's a failure.
            stdout, stderr = process.communicate(timeout=5)
            error_message = (
                f"❌ Test failed: App exited unexpectedly before timeout.\n"
                f"---EXIT CODE---\n{process.returncode}\n"
                f"---STDERR---\n{stderr}\n---STDOUT---\n{stdout}"
            )
            return error_message
        except subprocess.TimeoutExpired:
            # This is the SUCCESS case! The app ran for 5s without crashing.
            print("✅ Test successful: App process is stable.")
            process.terminate()  # Clean up the process
            try:
                process.wait(timeout=2)  # Wait for graceful shutdown
            except subprocess.TimeoutExpired:
                process.kill()  # Force kill if it doesn't respond
            return "✅ Test passed: App launched successfully."

    except Exception as e:
        return f"❌ An unexpected error occurred during testing: {str(e)}"


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
                install_package,
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
