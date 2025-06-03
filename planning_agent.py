"""
Smolagents CodeAgent for planning Gradio applications.

This module provides a specialized planning agent that can:
- Take a prompt describing a program
- Extensively plan how to implement the program using Python and Gradio
- Return an action, implementation and testing plan
"""

from smolagents import LiteLLMModel, ToolCallingAgent

from settings import settings


class GradioPlanningAgent:
    """
    A specialized CodeAgent for planning Gradio applications.

    This agent takes natural language descriptions of programs and creates
    comprehensive plans for implementing them with Python and Gradio.
    """

    def __init__(
        self,
        model_id: str | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
        verbosity_level: int | None = None,
    ):
        """
        Initialize the Gradio Planning Agent.

        Args:
            model_id: Model ID to use for planning (uses settings if None)
            api_base_url: API base URL (uses settings if None)
            api_key: API key (uses settings if None)
            verbosity_level: Level of verbosity for agent output (uses settings if None)
        """
        self.name = "planning_agent"
        self.description = """Expert software architect specializing in Gradio \
application planning.

This agent creates comprehensive, detailed plans for building Gradio applications \
based on user requirements.
It provides:
    - High-level action plans breaking down the implementation steps
    - Detailed technical implementation plans using Python and Gradio
    - Comprehensive testing strategies
    - Analysis of required Gradio components and dependencies
    - Complexity estimation for the project

The agent focuses purely on planning and architecture - no actual code \
implementation.
Perfect for getting structured, well-thought-out plans before development \
begins."""

        # Use settings as defaults, but allow override
        self.model_id = model_id or settings.model_id
        self.api_base_url = api_base_url or settings.api_base_url
        self.api_key = api_key or settings.api_key
        verbosity_level = verbosity_level or settings.planning_verbosity

        # Initialize the language model
        self.model = LiteLLMModel(
            model_id=self.model_id,
            api_base=self.api_base_url,
            api_key=self.api_key,
        )

        self.agent = ToolCallingAgent(
            model=self.model,
            tools=[],
            verbosity_level=verbosity_level,
            name=self.name,
            description=self.description,
        )

        self.system_prompt = """You are an expert software architect and Gradio \
application developer. Your role is to create comprehensive, detailed plans \
for building Gradio applications based on user requirements.

IMPORTANT: This is a PLANNING AND ARCHITECTURE phase only. Do NOT write any actual \
code. Focus on high-level design, structure, and planning. Code implementation will \
happen in a separate phase.

When given a description of a program to build, you must create three detailed plans:

1. **ACTION PLAN**: Break down the high-level steps needed to build the application
2. **IMPLEMENTATION PLAN**: Detailed technical implementation using Python and Gradio
3. **TESTING PLAN**: Comprehensive testing strategy for the application

For each plan, consider:
- Gradio components needed (gr.Textbox, gr.Button, gr.Chatbot, gr.Plot, etc.)
- Python dependencies and imports required
- Data flow and state management
- User interface design and user experience
- Error handling and edge cases
- Performance considerations
- Deployment considerations

You should structure your response using the following format:

## ACTION PLAN
[High-level steps and workflow]

## IMPLEMENTATION PLAN
[Detailed technical implementation with Gradio components]

## TESTING PLAN
[Comprehensive testing strategy]

## GRADIO COMPONENTS
[List of Gradio components that will be used]

## ESTIMATED COMPLEXITY
[Simple/Medium/Complex with brief explanation]

## DEPENDENCIES
[Required Python packages beyond gradio]

Be thorough, practical, and consider real-world constraints. Focus on creating \
maintainable, user-friendly Gradio applications. Remember: NO CODE IMPLEMENTATION \
at this stage - only architectural planning and structural design."""

    def __call__(self, task: str, **kwargs) -> str:
        """
        Handle planning tasks as a managed agent.

        Args:
            task: The user's description of the application to build
            **kwargs: Additional keyword arguments (ignored)

        Returns:
            String response containing the formatted planning result
        """
        full_prompt = f"""{self.system_prompt}

Create a comprehensive plan for building the following Gradio application:

{task}

Please provide detailed ACTION, IMPLEMENTATION, and TESTING plans following the \
specified format. Consider all aspects of the application including UI/UX, \
functionality, error handling, and deployment. /no_think"""

        try:
            return self.agent.run(full_prompt)

        except Exception as e:
            return f"❌ Planning failed: {str(e)}"


# Example usage and testing
if __name__ == "__main__":
    # Example of how to use the planning agent
    agent = GradioPlanningAgent()

    # Test with a simple calculator example
    result = agent(
        "Write a simple calculator app that can perform basic arithmetic operations"
    )

    print("=== PLANNING RESULT ===")
    print(result)
