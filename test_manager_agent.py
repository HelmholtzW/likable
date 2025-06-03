"""
Test cases for the Gradio Manager Agent.

This module contains unit tests and integration tests for the manager agent
functionality, including managed agent coordination and workflow testing.
"""

import unittest
from unittest.mock import Mock, patch

from manager_agent import (
    GradioManagerAgent,
    ManagerResult,
)


class TestGradioManagerAgent(unittest.TestCase):
    """Test the main GradioManagerAgent class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock settings
        self.mock_settings_patcher = patch("manager_agent.settings")
        self.mock_settings = self.mock_settings_patcher.start()

        # Set up mock settings
        self.mock_settings.manager_model_id = "test-manager-model"
        self.mock_settings.model_id = "test-model"
        self.mock_settings.code_model_id = "test-code-model"
        self.mock_settings.test_model_id = "test-test-model"
        self.mock_settings.api_base_url = "http://test.api"
        self.mock_settings.api_key = "test-key"
        self.mock_settings.manager_verbosity = 1
        self.mock_settings.planning_verbosity = 1
        self.mock_settings.coding_verbosity = 1
        self.mock_settings.testing_verbosity = 1
        self.mock_settings.max_manager_steps = 10
        self.mock_settings.max_coding_steps = 15
        self.mock_settings.max_testing_steps = 10

    def tearDown(self):
        """Clean up test fixtures."""
        self.mock_settings_patcher.stop()

    @patch("manager_agent.LiteLLMModel")
    @patch("manager_agent.ToolCallingAgent")
    @patch("manager_agent.GradioPlanningAgent")
    @patch("manager_agent.GradioCodingAgent")
    @patch("manager_agent.GradioTestingAgent")
    def test_manager_agent_initialization(
        self,
        mock_testing_agent,
        mock_coding_agent,
        mock_planning_agent,
        mock_tool_calling_agent,
        mock_litellm_model,
    ):
        """Test manager agent initialization."""
        # Mock the managed agents
        mock_planning_instance = Mock()
        mock_planning_instance.name = "planning_agent"
        mock_planning_instance.description = "Planning agent"
        mock_planning_agent.return_value = mock_planning_instance

        mock_coding_instance = Mock()
        mock_coding_instance.name = "coding_agent"
        mock_coding_instance.description = "Coding agent"
        mock_coding_agent.return_value = mock_coding_instance

        mock_testing_instance = Mock()
        mock_testing_instance.name = "testing_agent"
        mock_testing_instance.description = "Testing agent"
        mock_testing_agent.return_value = mock_testing_instance

        # Create manager agent
        manager = GradioManagerAgent()

        # Verify initialization
        self.assertIsInstance(manager, GradioManagerAgent)
        self.assertEqual(manager.max_iterations, 3)
        mock_litellm_model.assert_called_once()
        mock_tool_calling_agent.assert_called_once()

    @patch("manager_agent.LiteLLMModel")
    @patch("manager_agent.ToolCallingAgent")
    @patch("manager_agent.GradioPlanningAgent")
    @patch("manager_agent.GradioCodingAgent")
    @patch("manager_agent.GradioTestingAgent")
    def test_develop_application_success(
        self,
        mock_testing_agent,
        mock_coding_agent,
        mock_planning_agent,
        mock_tool_calling_agent,
        mock_litellm_model,
    ):
        """Test successful application development workflow."""
        # Mock the managed agents
        mock_planning_instance = Mock()
        mock_planning_instance.name = "planning_agent"
        mock_planning_instance.description = "Planning agent"
        mock_planning_agent.return_value = mock_planning_instance

        mock_coding_instance = Mock()
        mock_coding_instance.name = "coding_agent"
        mock_coding_instance.description = "Coding agent"
        mock_coding_agent.return_value = mock_coding_instance

        mock_testing_instance = Mock()
        mock_testing_instance.name = "testing_agent"
        mock_testing_instance.description = "Testing agent"
        mock_testing_agent.return_value = mock_testing_instance

        # Mock the main agent
        mock_agent_instance = Mock()
        mock_agent_instance.run.return_value = "Workflow completed successfully"
        mock_tool_calling_agent.return_value = mock_agent_instance

        # Create manager and test workflow
        manager = GradioManagerAgent()
        result = manager.develop_application("Create a simple calculator")

        # Verify the result
        self.assertIsInstance(result, ManagerResult)
        self.assertTrue(result.success)
        self.assertEqual(result.iterations, 1)
        self.assertIn("Workflow completed successfully", result.final_message)

    @patch("manager_agent.LiteLLMModel")
    @patch("manager_agent.ToolCallingAgent")
    @patch("manager_agent.GradioPlanningAgent")
    @patch("manager_agent.GradioCodingAgent")
    @patch("manager_agent.GradioTestingAgent")
    def test_develop_application_failure(
        self,
        mock_testing_agent,
        mock_coding_agent,
        mock_planning_agent,
        mock_tool_calling_agent,
        mock_litellm_model,
    ):
        """Test application development workflow failure handling."""
        # Mock the managed agents
        mock_planning_instance = Mock()
        mock_planning_instance.name = "planning_agent"
        mock_planning_instance.description = "Planning agent"
        mock_planning_agent.return_value = mock_planning_instance

        mock_coding_instance = Mock()
        mock_coding_instance.name = "coding_agent"
        mock_coding_instance.description = "Coding agent"
        mock_coding_agent.return_value = mock_coding_instance

        mock_testing_instance = Mock()
        mock_testing_instance.name = "testing_agent"
        mock_testing_instance.description = "Testing agent"
        mock_testing_agent.return_value = mock_testing_instance

        # Mock the main agent to raise an exception
        mock_agent_instance = Mock()
        mock_agent_instance.run.side_effect = Exception("Workflow failed")
        mock_tool_calling_agent.return_value = mock_agent_instance

        # Create manager and test workflow
        manager = GradioManagerAgent()
        result = manager.develop_application("Create a simple calculator")

        # Verify the error handling
        self.assertIsInstance(result, ManagerResult)
        self.assertFalse(result.success)
        self.assertEqual(result.iterations, 0)
        self.assertIn("Manager workflow failed", result.final_message)
        self.assertIn("Workflow failed", result.error_messages)

    def test_format_result_as_markdown_success(self):
        """Test formatting a successful result as markdown."""
        result = ManagerResult(
            success=True,
            planning_result=None,
            coding_result=None,
            testing_result=None,
            iterations=2,
            final_message="All steps completed successfully",
            error_messages=[],
        )

        manager = GradioManagerAgent()
        markdown = manager.format_result_as_markdown(result)

        self.assertIn("Development Workflow ✅", markdown)
        self.assertIn("Status**: Success", markdown)
        self.assertIn("Iterations**: 2", markdown)
        self.assertIn("All steps completed successfully", markdown)

    def test_format_result_as_markdown_failure(self):
        """Test formatting a failed result as markdown."""
        result = ManagerResult(
            success=False,
            planning_result=None,
            coding_result=None,
            testing_result=None,
            iterations=1,
            final_message="Workflow failed at planning stage",
            error_messages=["Planning agent error", "Configuration issue"],
        )

        manager = GradioManagerAgent()
        markdown = manager.format_result_as_markdown(result)

        self.assertIn("Development Workflow ❌", markdown)
        self.assertIn("Status**: Failed", markdown)
        self.assertIn("Iterations**: 1", markdown)
        self.assertIn("Workflow failed at planning stage", markdown)
        self.assertIn("Planning agent error", markdown)
        self.assertIn("Configuration issue", markdown)


if __name__ == "__main__":
    unittest.main()
