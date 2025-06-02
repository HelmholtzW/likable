"""
Smolagents CodeAgent for planning Gradio applications.

This module provides a specialized planning agent that can:
- Take a prompt describing a program
- Extensively plan how to implement the program using Python and Gradio
- Return an action, implementation and testing plan
"""

from dataclasses import dataclass

from smolagents import LiteLLMModel

from settings import settings


@dataclass
class PlanningResult:
    """Result of the planning agent containing structured plans."""

    action_plan: str
    implementation_plan: str
    testing_plan: str
    gradio_components: list[str]
    estimated_complexity: str
    dependencies: list[str]


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

        self.planning_prompt = """You are an expert software architect and Gradio \
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

    def plan_application(self, prompt: str) -> PlanningResult:
        """
        Create a comprehensive plan for a Gradio application based on the prompt.

        Args:
            prompt: Natural language description of the program to build

        Returns:
            PlanningResult containing structured plans
        """

        # Enhanced prompt for the agent
        user_prompt = f"""
Create a comprehensive plan for building the following Gradio application:

{prompt}

Please provide detailed ACTION, IMPLEMENTATION, and TESTING plans following the \
specified format. Consider all aspects of the application including UI/UX, \
functionality, error handling, and deployment.
"""

        messages = [
            {"role": "system", "content": self.planning_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = self.model.generate(messages)

        # Parse the response into structured result
        return self._parse_planning_response(response.content)

    def _parse_planning_response(self, response: str) -> PlanningResult:
        """
        Parse the agent's response into a structured PlanningResult.

        Args:
            response: Raw response from the planning agent

        Returns:
            Structured PlanningResult
        """

        # Initialize default values
        action_plan = ""
        implementation_plan = ""
        testing_plan = ""
        gradio_components = []
        estimated_complexity = "Medium"
        dependencies = ["gradio"]

        # Parse sections from the response
        sections = self._extract_sections(response)

        action_plan = sections.get("ACTION PLAN", "")
        implementation_plan = sections.get("IMPLEMENTATION PLAN", "")
        testing_plan = sections.get("TESTING PLAN", "")

        # Parse gradio components list
        components_text = sections.get("GRADIO COMPONENTS", "")
        if components_text:
            gradio_components = self._extract_list_items(components_text)

        # Parse complexity
        complexity_text = sections.get("ESTIMATED COMPLEXITY", "")
        if complexity_text:
            estimated_complexity = complexity_text.strip()

        # Parse dependencies
        deps_text = sections.get("DEPENDENCIES", "")
        if deps_text:
            dependencies = ["gradio"] + self._extract_list_items(deps_text)
            # Remove duplicates while preserving order
            dependencies = list(dict.fromkeys(dependencies))

        return PlanningResult(
            action_plan=action_plan,
            implementation_plan=implementation_plan,
            testing_plan=testing_plan,
            gradio_components=gradio_components,
            estimated_complexity=estimated_complexity,
            dependencies=dependencies,
        )

    def _extract_sections(self, text: str) -> dict[str, str]:
        """Extract sections from markdown-formatted text."""
        sections = {}
        current_section = None
        current_content = []

        for line in text.split("\n"):
            line = line.strip()

            # Check if line is a section header
            if line.startswith("## "):
                # Save previous section if exists
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _extract_list_items(self, text: str) -> list[str]:
        """Extract list items from text (handles bullet points, numbered lists, etc.)"""
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                # Remove common list prefixes
                if line.startswith("- "):
                    line = line[2:].strip()
                elif line.startswith("* "):
                    line = line[2:].strip()
                elif ". " in line and line.split(".")[0].isdigit():
                    line = line.split(".", 1)[1].strip()

                if line:
                    items.append(line)

        return items

    def format_plan_as_markdown(self, result: PlanningResult) -> str:
        """
        Format the planning result as a well-structured markdown document.

        Args:
            result: PlanningResult to format

        Returns:
            Markdown-formatted string
        """

        markdown = f"""# Gradio Application Plan

## 📋 Action Plan
{result.action_plan}

## 🔧 Implementation Plan
{result.implementation_plan}

## 🧪 Testing Plan
{result.testing_plan}

## 🎨 Gradio Components
{chr(10).join([f"- {component}" for component in result.gradio_components])}

## ⚡ Estimated Complexity
{result.estimated_complexity}

## 📦 Dependencies
{chr(10).join([f"- {dep}" for dep in result.dependencies])}
"""

        return markdown


# Example usage and testing
if __name__ == "__main__":
    # Example of how to use the planning agent
    agent = GradioPlanningAgent()

    # Test with a simple calculator example
    result = agent.plan_application(
        "Write a simple calculator app that can perform basic arithmetic operations"
    )

    print("=== PLANNING RESULT ===")
    print(agent.format_plan_as_markdown(result))
