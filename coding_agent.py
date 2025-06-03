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
from smolagents import LiteLLMModel, MCPClient, ToolCallingAgent

from planning_agent import PlanningResult
from settings import settings
from utils import load_file


@dataclass
class CodingResult:
    """Result of the coding agent containing implementation details."""

    success: bool
    project_path: str
    implemented_features: list[str]
    remaining_tasks: list[str]
    error_messages: list[str]
    final_app_code: str


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

        tool_collection = self.mcp_client.get_tools()

        # Initialize the CodeAgent with tools for file operations and project setup
        self.agent = ToolCallingAgent(
            model=self.model,
            tools=tool_collection,
            verbosity_level=verbosity_level,
            max_steps=max_steps,
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

    def setup_project_structure(self, project_name: str = "gradio_app") -> bool:
        """
        Set up the initial project structure using uv.

        Args:
            project_name: Name of the project

        Returns:
            bool: True if setup was successful
        """
        try:
            # Ensure sandbox directory exists and is clean
            if self.sandbox_path.exists():
                shutil.rmtree(self.sandbox_path)
            self.sandbox_path.mkdir(exist_ok=True)

            # Change to sandbox directory
            os.chdir(self.sandbox_path)

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
            os.chdir("../..")

            return True

        except subprocess.CalledProcessError as e:
            print(f"Error setting up project structure: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error setting up project: {e}")
            return False

    def implement_application(self, planning_result: PlanningResult) -> CodingResult:
        """
        Implement the full Gradio application based on the planning result.

        Args:
            planning_result: The planning result from the planning agent

        Returns:
            CodingResult containing implementation details
        """
        # Set up project structure
        project_name = "gradio_app"
        if not self.setup_project_structure(project_name):
            return CodingResult(
                success=False,
                project_path="",
                implemented_features=[],
                remaining_tasks=["Failed to set up project structure"],
                error_messages=["Could not initialize uv project"],
                final_app_code="",
            )

        project_path = str(self.sandbox_path / project_name)

        # Create comprehensive prompt for implementation
        gradio_components = chr(10).join(
            [f"- {comp}" for comp in planning_result.gradio_components]
        )
        dependencies = chr(10).join(
            [f"- {dep}" for dep in planning_result.dependencies if dep != "gradio"]
        )

        # Create the user prompt for the specific implementation
        user_prompt = f"""You are an expert Python developer and Gradio \
application architect.

Your task is to implement a complete, working Gradio application based on \
the provided plan.

PROJECT SETUP:
- You are working in the directory: {project_path}
- The project has been initialized with `uv` and `gradio` is already installed
- Use proper Python project structure with a main app.py file
- Add any additional dependencies needed using `uv add package_name`

IMPLEMENTATION REQUIREMENTS:
1. Create a complete, functional Gradio application in app.py
2. Follow the provided action plan and implementation plan exactly
3. Implement ALL gradio components mentioned in the plan
4. Add proper error handling and user feedback
5. Create a comprehensive README.md with usage instructions
6. Add all required dependencies to the project using `uv add`
7. Make sure the app can be run with `uv run python app.py`
8. Test the implementation and fix any issues

QUALITY STANDARDS:
- Write clean, well-documented code
- Use proper type hints where appropriate
- Follow Python best practices
- Add docstrings to functions and classes
- Handle edge cases and errors gracefully
- Make the UI intuitive and user-friendly
- When using multiline strings within multiline strings, properly escape them \
using triple quotes
  Example: Instead of using f\"\"\"...\"\"\", use f'''...''' or escape inner quotes \
like f\"\"\"...\\\"\\\"\\\"...\\\"\\\"\\\"...\"\"\"

GRADIO COMPONENTS TO IMPLEMENT:
{gradio_components}

DEPENDENCIES TO ADD:
{dependencies}

ACTION PLAN TO FOLLOW:
{planning_result.action_plan}

IMPLEMENTATION PLAN TO FOLLOW:
{planning_result.implementation_plan}

TESTING PLAN TO CONSIDER:
{planning_result.testing_plan}

You must implement the complete application and ensure it works properly.
Use subprocess to run `uv add` commands to install any needed packages.
Create all necessary files and make sure the application runs without errors.

Please implement the complete Gradio application based on the planning result.

The application should be fully functional and implement all the features
described in the plans.

Working directory: {project_path}

Please:
1. Start by creating/updating the README.md file with project description
   and usage instructions
2. Add any additional dependencies needed using `uv add package_name`
3. Create the complete app.py file with all the Gradio components and
   functionality
4. Test the implementation to ensure it works
5. Fix any issues that arise during testing

Make sure the final application is complete and functional.
/no_think
"""

        try:
            # Run the coding agent to implement the application
            self.agent.run(
                user_prompt,
                additional_args={
                    "current_app_py": load_file(str(Path(project_path) / "app.py")),
                },
            )

            # Check if the implementation was successful
            app_file = Path(project_path) / "app.py"
            if app_file.exists():
                with open(app_file, encoding="utf-8") as f:
                    final_app_code = f.read()

                return CodingResult(
                    success=True,
                    project_path=project_path,
                    implemented_features=planning_result.gradio_components,
                    remaining_tasks=[],
                    error_messages=[],
                    final_app_code=final_app_code,
                )
            else:
                return CodingResult(
                    success=False,
                    project_path=project_path,
                    implemented_features=[],
                    remaining_tasks=["Main app.py file was not created"],
                    error_messages=["Implementation failed to create app.py"],
                    final_app_code="",
                )

        except Exception as e:
            return CodingResult(
                success=False,
                project_path=project_path,
                implemented_features=[],
                remaining_tasks=["Complete implementation"],
                error_messages=[f"Coding agent error: {str(e)}"],
                final_app_code="",
            )

    def iterative_implementation(
        self, planning_result: PlanningResult, max_iterations: int = 3
    ) -> CodingResult:
        """
        Implement the application with iterative refinement.

        Args:
            planning_result: The planning result from the planning agent
            max_iterations: Maximum number of implementation iterations

        Returns:
            CodingResult containing final implementation details
        """
        last_result = None

        for iteration in range(max_iterations):
            print(f"🔄 Implementation iteration {iteration + 1}/{max_iterations}")

            # Implement or refine the application
            result = self.implement_application(planning_result)

            if result.success and not result.remaining_tasks:
                print(f"✅ Implementation successful in {iteration + 1} iteration(s)")
                return result

            last_result = result

            if iteration < max_iterations - 1:
                print(f"⚠️ Iteration {iteration + 1} incomplete. Refining...")
                # For subsequent iterations, we could modify the prompt to focus
                # on remaining tasks. This is a simplified version - in practice,
                # you'd want more sophisticated iteration logic

        print(f"⚠️ Implementation completed with {max_iterations} iterations")
        return last_result or CodingResult(
            success=False,
            project_path="",
            implemented_features=[],
            remaining_tasks=["Complete implementation failed"],
            error_messages=["Maximum iterations reached without completion"],
            final_app_code="",
        )


# Convenience function for the main app
def create_gradio_coding_agent() -> GradioCodingAgent:
    """Create a GradioCodingAgent with default settings."""
    return GradioCodingAgent()


if __name__ == "__main__":
    # Example usage
    from planning_agent import GradioPlanningAgent

    # Test with a simple planning result
    planning_agent = GradioPlanningAgent()
    planning_result = planning_agent.plan_application(
        "Create a simple text-to-text translator app"
    )

    # Create coding agent and implement
    coding_agent = create_gradio_coding_agent()
    coding_result = coding_agent.iterative_implementation(planning_result)

    print("Coding Result:")
    print(f"Success: {coding_result.success}")
    print(f"Project Path: {coding_result.project_path}")
    print(f"Implemented Features: {coding_result.implemented_features}")
    print(f"Remaining Tasks: {coding_result.remaining_tasks}")
    print(f"Error Messages: {coding_result.error_messages}")
