"""
Smolagents ToolCallingAgent for managing a multi-agent development workflow.

This module provides a manager agent that orchestrates:
- Planning Agent: Creates comprehensive plans for Gradio applications
- Coding Agent: Implements the planned applications with proper project structure
- Testing Agent: Tests and validates the implemented applications

The manager follows this workflow:
1. Receives user prompt
2. Hands prompt to Planning Agent → gets PlanningResult
3. Hands planning result to Coding Agent → gets CodingResult
4. Hands coding result to Testing Agent → gets TestingResult
5. If testing fails, hands errors back to Coding Agent for fixes
6. Continues until testing passes or max iterations reached
"""

from smolagents import CodeAgent, LiteLLMModel

from coding_agent import GradioCodingAgent
from planning_agent import GradioPlanningAgent
from settings import settings
from testing_agent import GradioTestingAgent


class GradioManagerAgent:
    """
    A manager agent that orchestrates the planning, coding, and testing workflow.

    This agent coordinates the entire development process from initial planning
    through implementation to final testing and validation.
    """

    def __init__(
        self,
        model_id: str | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
        verbosity_level: int | None = None,
        max_steps: int | None = None,
        max_iterations: int = 3,
    ):
        """
        Initialize the Gradio Manager Agent.

        Args:
            model_id: Model ID to use for management (uses settings if None)
            api_base_url: API base URL (uses settings if None)
            api_key: API key (uses settings if None)
            verbosity_level: Level of verbosity for agent output (uses settings if None)
            max_steps: Maximum number of management steps (uses settings if None)
            max_iterations: Maximum number of coding/testing iterations
        """
        self.name = "manager_agent"
        self.description = """Expert development manager coordinating multi-agent \
Gradio application development.

This agent orchestrates a complete development workflow by managing:
    - Planning Agent: Creates comprehensive application plans
    - Coding Agent: Implements planned applications with proper structure
    - Testing Agent: Validates and tests implemented applications

Coordinates iterative development cycles until applications are fully working \
and tested.
Provides comprehensive workflow management and detailed progress reporting."""

        # Use settings as defaults, but allow override
        self.model_id = model_id or settings.manager_model_id
        self.api_base_url = api_base_url or settings.api_base_url
        self.api_key = api_key or settings.api_key
        verbosity_level = verbosity_level or settings.manager_verbosity
        max_steps = max_steps or settings.max_manager_steps
        self.max_iterations = max_iterations

        # Initialize the language model
        self.model = LiteLLMModel(
            model_id=self.model_id,
            api_base=self.api_base_url,
            api_key=self.api_key,
        )

        # Create managed agent instances
        self.planning_agent = GradioPlanningAgent()
        self.coding_agent = GradioCodingAgent()
        self.testing_agent = GradioTestingAgent()

        # Initialize the main ToolCallingAgent with the managed agents
        self.agent = CodeAgent(
            model=self.model,
            tools=[],  # No tools needed, only managed agents
            managed_agents=[
                self.planning_agent,
                self.coding_agent,
                self.testing_agent,
            ],
            verbosity_level=verbosity_level,
            max_steps=max_steps,
            name=self.name,
            description=self.description,
        )

    def __call__(self, task: str, **kwargs) -> str:
        """
        Handle development management tasks as a managed agent.

        Args:
            task: The user's description of the application to build
            **kwargs: Additional keyword arguments (ignored)

        Returns:
            String response containing the formatted workflow result
        """
        try:
            # Run the development workflow
            result = self.develop_application(task)

            # Format the result for managed agent workflow
            return self.format_result_as_markdown(result)

        except Exception as e:
            return f"❌ Development workflow failed: {str(e)}"

    def develop_application(self, prompt: str) -> str:
        """
        Manage the full development workflow from planning to testing.

        Args:
            prompt: User's description of the application to build

        Returns:
            String containing the complete workflow results
        """
        try:
            # Create comprehensive task for the manager workflow
            manager_task = f"""You are a development manager coordinating a \
team of specialists to build a Gradio application.

The user wants: {prompt}

Please coordinate the following workflow:

1. **PLANNING PHASE**: Call the planning_agent to create a comprehensive \
plan for this application
2. **IMPLEMENTATION PHASE**: Call the coding_agent with the planning results \
to implement the application
3. **TESTING PHASE**: Call the testing_agent with the implementation results \
to test the application
4. **ITERATION**: If testing fails, call the coding_agent again with the \
error details to fix issues
5. **COMPLETION**: Continue until testing passes or maximum iterations reached

Start by calling the planning_agent with the user's request."""

            # Run the coordinated workflow
            result = self.agent.run(manager_task)

            # Return successful result with agent's response
            return str(result)

        except Exception as e:
            return f"Manager workflow failed: {str(e)}"


if __name__ == "__main__":
    # Example usage
    manager = GradioManagerAgent()

    # Test the manager workflow using managed agent approach
    result = manager("Create a simple calculator with basic arithmetic operations")

    print("=== MANAGER RESULT ===")
    print(result)
