"""
Test script for the Gradio Planning Agent.

This script demonstrates how to use the planning agent and tests it with
various prompts.
"""

from planning_agent import GradioPlanningAgent
from settings import settings


def test_planning_agent():
    """Test the planning agent with different prompts."""

    # Check if API_KEY is available
    if not settings.api_key:
        print("⚠️  Warning: API_KEY environment variable not set.")
        print("   You may need to set it for the agent to work properly.")
        print()

    # Display current settings
    print("Current Configuration:")
    print(f"   Model ID: {settings.model_id}")
    print(f"   API Key: {'***' if settings.api_key else 'None'}")
    print(f"   Verbosity: {settings.planning_verbosity}")
    print()

    # Initialize the planning agent
    print("🤖 Initializing Gradio Planning Agent...")
    agent = GradioPlanningAgent()
    print("✅ Agent initialized successfully!")
    print()

    # Test prompts for different types of applications
    test_prompts = [
        {
            "name": "Simple Calculator",
            "prompt": (
                "Write a simple calculator app that can perform basic "
                "arithmetic operations (addition, subtraction, multiplication, "
                "division)"
            ),
        },
        {
            "name": "Image Classifier",
            "prompt": (
                "Create an image classification app that allows users to "
                "upload an image and get predictions from a pre-trained model"
            ),
        },
        {
            "name": "Chat Interface",
            "prompt": (
                "Build a chatbot interface where users can have conversations "
                "with an AI assistant"
            ),
        },
        {
            "name": "Data Visualization Tool",
            "prompt": (
                "Create a data visualization tool that lets users upload CSV "
                "files and create different types of charts and plots"
            ),
        },
    ]

    # Test each prompt
    for i, test_case in enumerate(test_prompts, 1):
        print(f"🧪 Test {i}: {test_case['name']}")
        print(f"📝 Prompt: {test_case['prompt']}")
        print("-" * 80)

        try:
            # Run the planning agent
            result = agent.plan_application(test_case["prompt"])

            # Display results
            print("📊 Planning Results:")
            print(f"   Complexity: {result.estimated_complexity}")
            print(f"   Components: {', '.join(result.gradio_components[:3])}...")
            print(f"   Dependencies: {', '.join(result.dependencies[:3])}...")
            print()

            # Save detailed results to file
            filename = f"plan_{test_case['name'].lower().replace(' ', '_')}.md"
            with open(filename, "w") as f:
                f.write(agent.format_plan_as_markdown(result))
            print(f"💾 Detailed plan saved to: {filename}")

        except Exception as e:
            print(f"❌ Error testing {test_case['name']}: {e}")

        print("=" * 80)
        print()

    print("🎉 Testing completed!")


def demo_single_planning():
    """Demonstrate planning for a single application."""

    print("🎯 Single Application Planning Demo")
    print("=" * 50)

    # Get user input
    user_prompt = input("Enter your app description: ").strip()

    if not user_prompt:
        user_prompt = (
            "Create a simple todo list app where users can add, edit, "
            "and delete tasks"
        )
        print(f"Using default prompt: {user_prompt}")

    print("\n🤖 Planning your application...")

    try:
        # Initialize agent and run planning
        agent = GradioPlanningAgent()
        result = agent.plan_application(user_prompt)

        # Display formatted results
        print("\n" + "=" * 60)
        print(agent.format_plan_as_markdown(result))
        print("=" * 60)

        # Save to file
        with open("user_app_plan.md", "w") as f:
            f.write(agent.format_plan_as_markdown(result))
        print("\n💾 Plan saved to: user_app_plan.md")

    except Exception as e:
        print(f"❌ Error during planning: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_single_planning()
    else:
        test_planning_agent()
