"""
Smolagents CodeAgent for implementing Gradio applications.

This module provides a specialized coding agent that can:
- Take a planning result from the planning agent
- Set up a proper Python Gradio project structure in the sandbox folder
- Use uv for package management
- Implement the full plan with proper error handling and iterative development
- Only exit when the full plan is implemented
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mcp import StdioServerParameters
from smolagents import LiteLLMModel, MCPClient, ToolCallingAgent, tool

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
    Set up the initial project structure using uv.

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

        # Change back to workspace root
        os.chdir(original_cwd)

        return f"Successfully set up project structure for {project_name} \
in sandbox/{project_name}"

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


class GradioCodingAgent:
    """
    A specialized CodeAgent for implementing Gradio applications.

    This agent takes planning results and creates complete, working
    Gradio applications with proper project structure and dependencies.
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

This agent takes planning results and creates complete, working Gradio \
applications with:
    - Proper project structure using uv for package management
    - Complete implementation of all planned features
    - Working app.py file with functional Gradio interface
    - Proper dependency management and documentation
    - Error handling and iterative development approach

The agent only exits when the full plan is implemented successfully.
Handles complex applications and follows best practices for Python/Gradio \
development."""

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

        server_parameters = StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "sandbox",
            ],
        )

        self.mcp_client = MCPClient(server_parameters)

        # Get MCP tools and add our custom tools
        mcp_tools = self.mcp_client.get_tools()
        custom_tools = [setup_project_structure]
        all_tools = list(mcp_tools) + custom_tools

        # Initialize the CodeAgent with tools for file operations and project setup
        self.agent = ToolCallingAgent(
            model=self.model,
            tools=all_tools,
            verbosity_level=verbosity_level,
            max_steps=max_steps,
            name=self.name,
            description=self.description,
        )

        self.sandbox_path = Path("sandbox")

        # Store the original working directory for cleanup
        self.original_cwd = os.getcwd()

    def __del__(self):
        """
        Cleanup method called when the instance is about to be destroyed.

        This method ensures:
        - Working directory is restored to original location
        - Any open resources are properly closed
        - Temporary files are cleaned up if needed
        """
        try:
            # Restore original working directory
            if hasattr(self, "original_cwd") and os.path.exists(self.original_cwd):
                os.chdir(self.original_cwd)

            if hasattr(self, "mcp_client") and self.mcp_client:
                self.mcp_client.disconnect()

        except Exception:
            pass

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

Your mission is to implement a complete, working Gradio application based \
on the following architectural plan:

```
{task}
```

## Implementation Guidelines:

### 1. Project Setup
- ALWAYS start by calling setup_project_structure() to create the \
proper project structure
- Use uv for package management (already configured)
- The project will be created in ./sandbox/ directory

### 2. Implementation Requirements
- Create a complete, functional Gradio application
- Implement ALL features described in the plan
- Write clean, well-documented Python code
- Follow best practices for Gradio development
- Ensure proper error handling and user feedback

### 3. File Structure
- Create app.py as the main application file
- Add any necessary helper modules or utilities
- Include proper imports and dependencies
- Document code with comments and docstrings

### 4. Gradio Interface Guidelines
- Create an intuitive and user-friendly interface
- Use appropriate Gradio components for each feature
- Implement proper input validation and error handling
- Ensure responsive design and good UX practices
- Add helpful descriptions and examples where needed

### 5. Quality Standards
- Test your implementation thoroughly
- Handle edge cases and error scenarios
- Provide clear feedback to users
- Ensure the app runs without errors
- Follow Python coding standards (PEP 8)

### 6. Completion Criteria
- All planned features are fully implemented
- The application runs successfully with `python app.py`
- Users can interact with all described functionality
- Code is clean, documented, and maintainable

Remember: You can ONLY access files in the ./sandbox directory.
Do not attempt to access files outside this sandbox environment.

Start by setting up the project structure, then implement each feature \
systematically until the complete application is ready."""

        try:
            return self.agent.run(full_prompt)

        except Exception as e:
            return f"❌ Implementation failed: {str(e)}"


if __name__ == "__main__":
    # Example usage
    from planning_agent import GradioPlanningAgent

    # Test with a simple planning result
    planning_agent = GradioPlanningAgent()
    planning_result = planning_agent("Create a simple calculator app")

    # Create coding agent and implement using managed agent approach
    coding_agent = GradioCodingAgent()
    coding_result_str = coding_agent(planning_result)

    print("=== CODING RESULT ===")
    print(coding_result_str)
