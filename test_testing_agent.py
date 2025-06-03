"""
Test cases for the Gradio Testing Agent.

This module contains unit tests and integration tests for the testing agent
functionality, including tool validation and agent behavior testing.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from coding_agent import CodingResult
from testing_agent import (
    GradioTestingAgent,
    TestingResult,
    check_app_health,
    create_gradio_testing_agent,
    run_gradio_app,
    setup_venv_with_uv,
    stop_gradio_processes,
    test_gradio_ui_basic,
)


class TestTestingAgentTools(unittest.TestCase):
    """Test the individual tools used by the testing agent."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = str(Path(self.temp_dir) / "test_project")
        os.makedirs(self.project_path, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_setup_venv_with_uv_missing_directory(self):
        """Test setup_venv_with_uv with non-existent directory."""
        result = setup_venv_with_uv("/non/existent/path")
        self.assertIn("Error: Project directory", result)
        self.assertIn("does not exist", result)

    @patch("subprocess.run")
    def test_setup_venv_with_uv_success(self, mock_run):
        """Test successful virtual environment setup."""
        mock_run.return_value = Mock(returncode=0)

        result = setup_venv_with_uv(self.project_path)

        self.assertIn("Successfully set up virtual environment", result)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_setup_venv_with_uv_failure(self, mock_run):
        """Test failed virtual environment setup."""
        mock_run.return_value = Mock(returncode=1, stderr="uv error")

        result = setup_venv_with_uv(self.project_path)

        self.assertIn("Error setting up venv", result)
        self.assertIn("uv error", result)

    def test_run_gradio_app_missing_file(self):
        """Test run_gradio_app with missing app.py file."""
        result = run_gradio_app(self.project_path)
        self.assertIn("Error: app.py not found", result)

    @patch("subprocess.Popen")
    def test_run_gradio_app_success(self, mock_popen):
        """Test successful Gradio app launch."""
        # Create app.py file
        app_file = Path(self.project_path) / "app.py"
        app_file.write_text("import gradio as gr\nprint('test')")

        # Mock the process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        result = run_gradio_app(self.project_path, timeout=1)

        self.assertIn("Successfully started Gradio app", result)
        mock_popen.assert_called_once()

    @patch("requests.get")
    def test_check_app_health_success(self, mock_get):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_get.return_value = mock_response

        result = check_app_health()

        self.assertIn("Application is healthy", result)
        self.assertIn("0.50s", result)

    @patch("requests.get")
    def test_check_app_health_connection_error(self, mock_get):
        """Test health check with connection error."""
        mock_get.side_effect = Exception("Connection failed")

        result = check_app_health()

        self.assertIn("Error checking application health", result)

    def test_test_gradio_ui_basic_selenium_not_installed(self):
        """Test UI testing when Selenium is not available."""
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'selenium'")
        ):
            result = test_gradio_ui_basic()
            self.assertIn("Error: Selenium not installed", result)

    @patch("subprocess.run")
    def test_stop_gradio_processes(self, mock_run):
        """Test stopping Gradio processes."""
        # Mock subprocess calls
        mock_run.side_effect = [
            Mock(returncode=0),  # pkill successful
            Mock(stdout="12345\n67890", returncode=0),  # lsof
            Mock(returncode=0),  # kill first process
            Mock(returncode=0),  # kill second process
        ]

        result = stop_gradio_processes()

        self.assertIn("Stopped Gradio processes by name", result)
        self.assertIn("Killed process 12345", result)
        self.assertIn("Killed process 67890", result)


class TestGradioTestingAgent(unittest.TestCase):
    """Test the main GradioTestingAgent class."""

    @patch("testing_agent.settings")
    def setUp(self, mock_settings):
        """Set up test fixtures."""
        mock_settings.test_model_id = "test-model"
        mock_settings.api_base_url = "http://test.api"
        mock_settings.api_key = "test-key"
        mock_settings.testing_verbosity = 1
        mock_settings.max_testing_steps = 10

    @patch("testing_agent.LiteLLMModel")
    @patch("testing_agent.ToolCallingAgent")
    def test_agent_initialization(self, mock_agent, mock_model):
        """Test agent initialization with default settings."""
        agent = GradioTestingAgent()

        self.assertIsInstance(agent, GradioTestingAgent)
        mock_model.assert_called_once()
        mock_agent.assert_called_once()

    def test_test_application_with_failed_coding_result(self):
        """Test testing application when coding agent failed."""
        agent = GradioTestingAgent()
        failed_coding_result = CodingResult(
            success=False,
            project_path="/test/path",
            implemented_features=[],
            remaining_tasks=["Setup failed"],
            error_messages=["Setup error"],
            final_app_code="",
        )

        result = agent.test_application(failed_coding_result)

        self.assertFalse(result.success)
        self.assertEqual(result.project_path, "/test/path")
        self.assertIn(
            "Coding agent failed to create application", result.test_cases_failed
        )

    @patch("testing_agent.ToolCallingAgent")
    def test_test_application_agent_error(self, mock_agent_class):
        """Test testing application when agent execution fails."""
        mock_agent = Mock()
        mock_agent.run.side_effect = Exception("Agent error")
        mock_agent_class.return_value = mock_agent

        agent = GradioTestingAgent()
        successful_coding_result = CodingResult(
            success=True,
            project_path="/test/path",
            implemented_features=["Basic UI"],
            remaining_tasks=[],
            error_messages=[],
            final_app_code="import gradio as gr",
        )

        result = agent.test_application(successful_coding_result)

        self.assertFalse(result.success)
        self.assertIn("Testing agent execution failed", result.test_cases_failed)

    def test_parse_testing_response_success(self):
        """Test parsing a successful testing response."""
        agent = GradioTestingAgent()
        response = """
        Successfully set up virtual environment for /test/path
        Successfully started Gradio app: Server running
        Application is healthy. Status: 200, Response time: 0.25s
        ✓ Page loaded successfully; ✓ Gradio container found
        Screenshot saved to /tmp/test.png
        """

        result = agent._parse_testing_response(response, "/test/path")

        self.assertTrue(result.success)
        self.assertTrue(result.setup_successful)
        self.assertTrue(result.server_launched)
        self.assertTrue(result.ui_accessible)
        self.assertIn("Virtual environment setup", result.test_cases_passed)
        self.assertIn("UI component testing", result.test_cases_passed)
        self.assertEqual(result.performance_metrics["response_time_seconds"], 0.25)

    def test_parse_testing_response_failure(self):
        """Test parsing a failed testing response."""
        agent = GradioTestingAgent()
        response = """
        Error setting up venv: Command failed
        Error running gradio app: File not found
        Cannot connect to http://127.0.0.1:7860
        Error during UI testing: Browser error
        """

        result = agent._parse_testing_response(response, "/test/path")

        self.assertFalse(result.success)
        self.assertFalse(result.setup_successful)
        self.assertFalse(result.server_launched)
        self.assertFalse(result.ui_accessible)

    def test_generate_test_report(self):
        """Test generating a test report."""
        agent = GradioTestingAgent()
        test_result = TestingResult(
            success=True,
            project_path="/test/path",
            setup_successful=True,
            server_launched=True,
            ui_accessible=True,
            test_cases_passed=["Setup", "Launch", "UI"],
            test_cases_failed=[],
            error_messages=[],
            screenshots=["/tmp/test.png"],
            performance_metrics={"response_time": 0.5},
            logs="Test completed successfully",
        )

        report = agent.generate_test_report(test_result)

        self.assertIn("# Gradio Application Test Report ✅", report)
        self.assertIn("**Project Path**: `/test/path`", report)
        self.assertIn("✅ Setup", report)
        self.assertIn("✅ Launch", report)
        self.assertIn("✅ UI", report)
        self.assertIn("/tmp/test.png", report)


class TestTestingAgentFactory(unittest.TestCase):
    """Test the factory function for creating testing agents."""

    @patch("testing_agent.GradioTestingAgent")
    def test_create_gradio_testing_agent(self, mock_agent_class):
        """Test creating a testing agent with factory function."""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        agent = create_gradio_testing_agent()

        self.assertEqual(agent, mock_agent)
        mock_agent_class.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
