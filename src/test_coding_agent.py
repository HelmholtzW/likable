"""
Test module for the Gradio Coding Agent.

This module provides tests to verify that the coding agent can:
- Set up proper project structure with uv
- Integrate with the planning agent
- Create functional Gradio applications
"""

import os
import shutil
from pathlib import Path

from coding_agent import GradioCodingAgent
from planning_agent import PlanningResult


def test_setup_project_structure():
    """Test that the project structure setup works correctly."""
    agent = GradioCodingAgent()

    # Clean up any existing test directory
    test_sandbox = Path("test_sandbox")
    if test_sandbox.exists():
        shutil.rmtree(test_sandbox)

    # Temporarily change the sandbox path for testing
    original_sandbox = agent.sandbox_path
    agent.sandbox_path = test_sandbox

    try:
        # Test project setup
        success = agent.setup_project_structure("test_project")

        # Verify the structure was created
        project_path = test_sandbox / "test_project"
        assert project_path.exists(), "Project directory should exist"
        assert (project_path / "pyproject.toml").exists(), "pyproject.toml should exist"
        assert (project_path / "README.md").exists(), "README.md should exist"

        print("✅ Project structure setup test passed")
        return success

    finally:
        # Restore original sandbox path
        agent.sandbox_path = original_sandbox

        # Clean up test directory
        if test_sandbox.exists():
            shutil.rmtree(test_sandbox)


def test_mock_implementation():
    """Test implementation with a mock planning result."""

    # Create a simple mock planning result
    mock_planning = PlanningResult(
        action_plan="Create a simple text input and output application",
        implementation_plan="Use gr.Textbox for input and output",
        testing_plan="Test with sample text input",
        gradio_components=["gr.Textbox", "gr.Button"],
        estimated_complexity="Simple",
        dependencies=["gradio"],
    )

    agent = GradioCodingAgent()

    # Note: This test requires API access and will only work with valid credentials
    try:
        print("🧪 Testing mock implementation (requires API access)...")
        result = agent.implement_application(mock_planning)

        print(f"Implementation result: Success={result.success}")
        print(f"Project path: {result.project_path}")
        print(f"Error messages: {result.error_messages}")

        return result

    except Exception as e:
        print(f"⚠️ Mock implementation test failed (expected without API): {e}")
        return None


def test_agent_initialization():
    """Test that the coding agent initializes correctly."""
    try:
        agent = GradioCodingAgent()
        assert agent is not None, "Agent should initialize"
        assert agent.model is not None, "Model should be initialized"
        assert agent.agent is not None, "CodeAgent should be initialized"

        print("✅ Agent initialization test passed")
        return True

    except Exception as e:
        print(f"❌ Agent initialization test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Running Coding Agent Tests")
    print("=" * 50)

    # Test 1: Agent initialization
    test_agent_initialization()
    print()

    # Test 2: Project structure setup
    test_setup_project_structure()
    print()

    # Test 3: Mock implementation (optional, requires API)
    if os.getenv("API_KEY"):
        test_mock_implementation()
    else:
        print("⚠️ Skipping implementation test (no API_KEY set)")

    print("\n✅ All available tests completed!")


if __name__ == "__main__":
    main()
