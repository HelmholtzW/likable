"""
Smolagents CodeAgent for implementing Gradio applications using whole edit format.

This module provides a specialized coding agent that can:
- Take a planning result from the planning agent
- Set up a proper Python Gradio project structure in the sandbox folder
- Use uv for package management
- Implement the full plan using whole edit format (aider-style)
- Focus exclusively on app.py file
- Only exit when the full plan is implemented
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from smolagents import LiteLLMModel, ToolCallingAgent, tool

from settings import settings


@dataclass
class CodingResult:
    """Result of the coding agent containing implementation details."""

    success: bool
    project_path: str
    implemented_features: list[str]
    remaining_tasks: list[str]
    error_messages: list[str]
    final_app_code: str


@tool
def setup_project_structure(project_name: str = "gradio_app") -> str:
    """
    Set up the initial project structure using uv with minimal files.

    Args:
        project_name: Name of the project

    Returns:
        Status message indicating success or failure
    """
    try:
        sandbox_path = Path("sandbox")

        # Ensure sandbox directory exists and is clean
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)
        sandbox_path.mkdir(exist_ok=True)

        # Store original working directory
        original_cwd = os.getcwd()

        # Change to sandbox directory
        os.chdir(sandbox_path)

        # Initialize with uv
        subprocess.run(
            ["uv", "init", project_name],
            capture_output=True,
            text=True,
            check=True,
        )

        # Change to project directory
        os.chdir(project_name)

        # Add gradio as a dependency
        subprocess.run(
            ["uv", "add", "gradio"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Create initial app.py file
        app_content = """import gradio as gr

def main():
    # TODO: Implement Gradio application
    demo = gr.Interface(
        fn=lambda x: f"Hello {x}!",
        inputs="text",
        outputs="text",
        title="Gradio App"
    )
    return demo

if __name__ == "__main__":
    demo = main()
    # Never change the port, otherwise the preview app will not work!
    demo.launch(server_name="0.0.0.0", server_port=7861)
"""

        with open("app.py", "w") as f:
            f.write(app_content)

        # Change back to workspace root
        os.chdir(original_cwd)

        return (
            f"Successfully set up project structure for {project_name} "
            f"in sandbox/{project_name} with initial app.py"
        )

    except subprocess.CalledProcessError as e:
        # Restore working directory on error
        try:
            os.chdir(original_cwd)
        except NameError:
            pass
        return f"Error setting up project structure: {e.stderr}"
    except Exception as e:
        # Restore working directory on error
        try:
            os.chdir(original_cwd)
        except NameError:
            pass
        return f"Unexpected error setting up project: {str(e)}"


@tool
def read_current_app_py(project_name: str = "gradio_app") -> str:
    """
    Read the current content of app.py to provide context for editing.

    Args:
        project_name: Name of the project

    Returns:
        Current content of app.py or error message
    """
    try:
        app_path = Path("sandbox") / project_name / "app.py"

        if not app_path.exists():
            return "app.py does not exist yet. Use setup_project_structure first."

        with open(app_path) as f:
            content = f.read()

        return f"Current app.py content:\n\n{content}"

    except Exception as e:
        return f"Error reading app.py: {str(e)}"


@tool
def apply_whole_edit(new_content: str, project_name: str = "gradio_app") -> str:
    """
    Apply a whole file edit to app.py using aider's whole edit format.

    The input should be in the format:
    app.py
    ```python
    [complete file content]
    ```

    Args:
        new_content: The new complete content for app.py in whole edit format
        project_name: Name of the project

    Returns:
        Status message indicating success or failure
    """
    try:
        # Parse the whole edit format
        lines = new_content.strip().split("\n")

        # Look for the filename line and code block
        filename_found = False
        code_start_idx = -1
        code_end_idx = -1

        for i, line in enumerate(lines):
            # Check if line contains just the filename
            if line.strip() == "app.py":
                filename_found = True
                continue

            # Look for code block start after filename
            if filename_found and line.strip().startswith("```"):
                if code_start_idx == -1:
                    code_start_idx = i + 1
                else:
                    code_end_idx = i
                    break

        if not filename_found:
            return "Error: Expected filename 'app.py' not found in edit format"

        if code_start_idx == -1:
            return "Error: No code block found after filename"

        # Extract the code content
        if code_end_idx == -1:
            # Code block extends to end of input
            code_lines = lines[code_start_idx:]
        else:
            code_lines = lines[code_start_idx:code_end_idx]

        # Join the code lines
        new_app_content = "\n".join(code_lines)

        # Write to app.py
        app_path = Path("sandbox") / project_name / "app.py"

        if not app_path.parent.exists():
            return f"Error: Project directory {app_path.parent} does not exist"

        with open(app_path, "w") as f:
            f.write(new_app_content)

        return f"Successfully updated app.py with {len(code_lines)} lines of code"

    except Exception as e:
        return f"Error applying whole edit: {str(e)}"


@tool
def apply_diff_edit(diff_content: str, project_name: str = "gradio_app") -> str:
    """
    Apply a diff edit to app.py using aider's diff edit format.

    The input should be in the format:
    app.py
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
        project_name: Name of the project

    Returns:
        Status message indicating success or failure
    """
    try:
        app_path = Path("sandbox") / project_name / "app.py"

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
def test_app_py(project_name: str = "gradio_app") -> str:
    """
    Test if the current app.py runs without syntax errors.

    Args:
        project_name: Name of the project

    Returns:
        Test result message
    """
    try:
        app_path = Path("sandbox") / project_name / "app.py"

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


class GradioCodingAgent:
    """
    A specialized CodeAgent for implementing Gradio applications.

    This agent takes planning results and creates complete, working
    Gradio applications with focus exclusively on app.py.
    """

    def __init__(
        self,
        model_id: str | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
        verbosity_level: int | None = None,
        max_steps: int | None = None,
    ):
        """
        Initialize the Gradio Coding Agent.

        Args:
            model_id: Model ID to use for coding (uses settings if None)
            api_base_url: API base URL (uses settings if None)
            api_key: API key (uses settings if None)
            verbosity_level: Level of verbosity for agent output (uses settings if None)
            max_steps: Maximum number of coding steps (uses settings if None)
        """
        self.name = "coding_agent"
        self.description = """Expert Python developer specializing in Gradio \
application implementation.

This agent takes planning results and creates complete, working Gradio applications by:
    - Setting up proper project structure using uv for package management
    - Implementing all planned features exclusively in app.py
    - Using whole edit format for file modifications
    - Following best practices for Python/Gradio development
    - Only working with app.py - no other files or folders

The agent only exits when the full plan is implemented successfully in app.py."""

        # Use settings as defaults, but allow override
        self.model_id = model_id or settings.code_model_id
        self.api_base_url = api_base_url or settings.api_base_url
        self.api_key = api_key or settings.api_key
        verbosity_level = verbosity_level or settings.coding_verbosity
        max_steps = max_steps or settings.max_coding_steps

        # Initialize the language model for the CodeAgent
        self.model = LiteLLMModel(
            model_id=self.model_id,
            api_base=self.api_base_url,
            api_key=self.api_key,
        )

        # Custom tools for whole edit format
        custom_tools = [
            setup_project_structure,
            read_current_app_py,
            apply_whole_edit,
            apply_diff_edit,
            test_app_py,
        ]

        # Initialize the CodeAgent with tools for whole edit format
        self.agent = ToolCallingAgent(
            model=self.model,
            tools=custom_tools,
            verbosity_level=verbosity_level,
            max_steps=max_steps,
            name=self.name,
            description=self.description,
        )

        self.sandbox_path = Path("sandbox")

    def __call__(self, task: str, **kwargs) -> str:
        """
        Handle coding tasks as a managed agent.

        Args:
            task: The planning result or task description
            **kwargs: Additional keyword arguments (ignored)

        Returns:
            String response containing the formatted coding result
        """
        full_prompt = f"""You are an expert Python developer specializing in \
Gradio application implementation.

Your mission is to implement or fix a Gradio application based on the following task:

{task}

## Initial Assessment

FIRST, determine if you need to create a new project or work with an existing one:

1. Call read_current_app_py() to check if there's already an app.py file
2. Based on the result:
   - If app.py doesn't exist: Set up a new project structure
   - If app.py exists: Work with the existing project to implement changes or fix issues

## Implementation Guidelines:

### 1. Project Setup (Only for New Projects)
- If no app.py exists, call setup_project_structure() to create the proper \
project structure

### 2. Edit Formats
You have TWO editing formats available. Choose the most appropriate one:

#### A. Whole Edit Format (for major changes or new files)
Use when making large changes or rewriting significant portions:

1. First call read_current_app_py() to see the current content
2. Then call apply_whole_edit() with the COMPLETE new file content in this exact format:

app.py
```python
[complete file content here - every single line of the new app.py]
```

#### B. Diff Edit Format (for small targeted changes)
Use when making small, targeted changes to existing code:

1. First call read_current_app_py() to see the current content
2. Then call apply_diff_edit() with search/replace blocks in this exact format:

app.py
```
<<<<<<< SEARCH
[exact text to find and replace]
=======
[new text to replace it with]
>>>>>>> REPLACE
```

For multiple changes in the same file, use multiple search/replace blocks:

app.py
```
<<<<<<< SEARCH
def calculate_add(a, b):
    return a + b
=======
def calculate_add(a, b):
    \"""Add two numbers together.\"""
    return a + b
>>>>>>> REPLACE

<<<<<<< SEARCH
title="Simple Calculator"
=======
title="Advanced Calculator with History"
>>>>>>> REPLACE

<<<<<<< SEARCH
    # Basic interface
    demo = gr.Interface(
=======
    # Enhanced interface with validation
    demo = gr.Interface(
>>>>>>> REPLACE
```

Important: Each search block must contain EXACT text that exists in the file \
(case-sensitive, whitespace-sensitive).

### 3. App.py Only Development
- You work EXCLUSIVELY with app.py - no other files
- All functionality must be implemented in this single file
- No separate modules, no README, no documentation files
- Just one complete, self-contained app.py

### 4. Implementation Requirements
- Create or modify a complete, functional Gradio application in app.py
- Implement ALL features described in the plan or fix ALL issues mentioned
- Write clean, well-documented Python code with docstrings
- Follow best practices for Gradio development
- Ensure proper error handling and user feedback
- Include all necessary imports at the top

### 5. Gradio Interface Guidelines
- Create an intuitive and user-friendly interface
- Use appropriate Gradio components for each feature
- Implement proper input validation and error handling
- Ensure responsive design and good UX practices
- Add helpful descriptions and examples where needed
- The app should launch with demo.launch(server_name="0.0.0.0", \
server_port=7861) at the end

### 6. Quality Standards
- Test your implementation with test_app_py() after each edit
- Handle edge cases and error scenarios
- Provide clear feedback to users
- Ensure the app runs without errors
- Follow Python coding standards (PEP 8)

### 7. Iterative Development Process
1. Check if app.py exists with read_current_app_py()
2. If no app.py: Setup project structure first
3. If app.py exists: Analyze current content and issues
4. Plan your changes based on the task requirements
5. Choose appropriate edit format:
   - Use apply_whole_edit() for major changes/rewrites
   - Use apply_diff_edit() for small targeted changes
6. Test with test_app_py()
7. Repeat until all features are implemented or all issues are fixed

### 8. Completion Criteria
- All planned features are fully implemented in app.py OR all reported issues are fixed
- The application passes syntax tests
- Users can interact with all described functionality
- Code is clean, documented, and maintainable
- Single app.py file contains everything needed

Remember:
- ALWAYS start by checking if app.py exists with read_current_app_py()
- Only setup new project structure if app.py doesn't exist
- Use apply_whole_edit() for major changes or rewrites
- Use apply_diff_edit() for small targeted changes
- Use test_app_py() to verify your changes work
- NEVER work with any other files - only app.py

Start by assessing the current state, if necessary, come up with a project_name, \
then implement features or fix issues systematically until the complete application \
is ready in app.py. /no_think"""

        try:
            return self.agent.run(full_prompt)

        except Exception as e:
            return f"❌ Implementation failed: {str(e)}"


if __name__ == "__main__":
    coding_agent = GradioCodingAgent()
    coding_result_str = coding_agent("Create a simple calculator app")

    print("=== CODING RESULT ===")
    print(coding_result_str)
