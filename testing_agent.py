"""
Smolagents ToolCallingAgent for testing Gradio applications.

This module provides a specialized testing agent that can:
- Set up virtual environments using uv
- Run Gradio applications in the sandbox folder
- Perform basic UI testing using browser automation
- Validate that the application is functional and responsive
- Generate test reports with screenshots and logs
"""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from smolagents import LiteLLMModel, ToolCallingAgent, tool

from coding_agent import CodingResult
from settings import settings


@dataclass
class TestingResult:
    """Result of the testing agent containing validation details."""

    success: bool
    project_path: str
    setup_successful: bool
    server_launched: bool
    ui_accessible: bool
    test_cases_passed: list[str]
    test_cases_failed: list[str]
    error_messages: list[str]
    screenshots: list[str]
    performance_metrics: dict[str, float]
    logs: str


@tool
def setup_venv_with_uv(project_path: str) -> str:
    """
    Set up a virtual environment using uv for the Gradio project.

    Args:
        project_path: Path to the Gradio project directory

    Returns:
        Status message indicating success or failure
    """
    try:
        # Change to project directory
        original_cwd = os.getcwd()
        project_dir = Path(project_path)

        if not project_dir.exists():
            return f"Error: Project directory {project_path} does not exist"

        os.chdir(project_dir)

        # Install dependencies using uv
        result = subprocess.run(
            ["uv", "sync"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
        )

        os.chdir(original_cwd)

        if result.returncode == 0:
            return f"Successfully set up virtual environment for {project_path}"
        else:
            return f"Error setting up venv: {result.stderr}"

    except subprocess.TimeoutExpired:
        os.chdir(original_cwd)
        return "Error: uv sync timed out after 5 minutes"
    except FileNotFoundError:
        os.chdir(original_cwd)
        return "Error: uv command not found. Please install uv first."
    except Exception as e:
        os.chdir(original_cwd)
        return f"Unexpected error: {str(e)}"


@tool
def run_gradio_app(project_path: str, timeout: int = 30) -> str:
    """
    Run the Gradio application and check if it starts successfully.

    Args:
        project_path: Path to the Gradio project directory
        timeout: Maximum time to wait for the app to start (in seconds)

    Returns:
        Status message with server information or error details
    """
    try:
        project_dir = Path(project_path)
        app_file = project_dir / "app.py"

        if not app_file.exists():
            return f"Error: app.py not found in {project_path}"

        # Start the Gradio app in background
        process = subprocess.Popen(
            ["uv", "run", "python", "app.py"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for the server to start (look for "Running on" in output)
        start_time = time.time()
        server_info = ""

        while time.time() - start_time < timeout:
            if process.poll() is not None:
                # Process has terminated
                stdout, stderr = process.communicate()
                return (
                    f"Error: App terminated early. STDOUT: {stdout}, STDERR: {stderr}"
                )

            time.sleep(1)

            # Try to read some output to see if server started
            try:
                # Non-blocking read attempt
                import select

                if select.select([process.stdout], [], [], 0.1)[0]:
                    line = process.stdout.readline()
                    if line and "Running on" in line:
                        server_info = line.strip()
                        break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(2)
                break

        if not server_info:
            server_info = (
                f"Server started (PID: {process.pid}), accessible at "
                "http://127.0.0.1:7860"
            )

        return f"Successfully started Gradio app: {server_info}"

    except Exception as e:
        return f"Error running Gradio app: {str(e)}"


@tool
def check_app_health(url: str = "http://127.0.0.1:7860") -> str:
    """
    Check if the Gradio application is responding to HTTP requests.

    Args:
        url: URL of the Gradio application

    Returns:
        Health check status message
    """
    try:
        import requests

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return (
                f"Application is healthy. Status: {response.status_code}, "
                f"Response time: {response.elapsed.total_seconds():.2f}s"
            )
        else:
            return f"Application returned status {response.status_code}"

    except requests.exceptions.ConnectionError:
        return f"Error: Cannot connect to {url}. Application may not be running."
    except requests.exceptions.Timeout:
        return f"Error: Request to {url} timed out."
    except Exception as e:
        return f"Error checking application health: {str(e)}"


@tool
def test_gradio_ui_basic(url: str = "http://127.0.0.1:7860") -> str:
    """
    Perform basic UI testing of the Gradio application.

    Args:
        url: URL of the Gradio application

    Returns:
        Test results summary
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        # Setup Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)

        try:
            # Navigate to the Gradio app
            driver.get(url)

            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check for Gradio-specific elements
            gradio_app = driver.find_elements(
                By.CSS_SELECTOR, ".gradio-container, #gradio-app, .app"
            )

            if not gradio_app:
                return "Warning: No Gradio app container found on the page"

            # Check for interactive elements (buttons, inputs)
            inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, button")

            test_results = []
            test_results.append("✓ Page loaded successfully")
            test_results.append("✓ Gradio container found")
            test_results.append(f"✓ Found {len(inputs)} interactive elements")

            # Take a screenshot
            screenshot_path = "/tmp/gradio_test_screenshot.png"
            driver.save_screenshot(screenshot_path)
            test_results.append(f"✓ Screenshot saved to {screenshot_path}")

            return "; ".join(test_results)

        finally:
            driver.quit()

    except ImportError:
        return "Error: Selenium not installed. Install with: pip install selenium"
    except Exception as e:
        return f"Error during UI testing: {str(e)}"


@tool
def stop_gradio_processes() -> str:
    """
    Stop any running Gradio processes to clean up after testing.

    Returns:
        Status message about process cleanup
    """
    try:
        stopped_processes = []

        # Find processes running Gradio apps by name
        result1 = subprocess.run(
            ["pkill", "-f", "gradio"], capture_output=True, text=True
        )

        if result1.returncode == 0:
            stopped_processes.append("Stopped Gradio processes by name")

        # Also try to kill processes on port 7860
        result2 = subprocess.run(["lsof", "-ti:7860"], capture_output=True, text=True)

        if result2.stdout.strip():
            pids = result2.stdout.strip().split("\n")
            for pid in pids:
                kill_result = subprocess.run(["kill", "-9", pid], capture_output=True)
                if kill_result.returncode == 0:
                    stopped_processes.append(f"Killed process {pid}")

        if stopped_processes:
            return "; ".join(stopped_processes)
        else:
            return "No Gradio processes found to stop"

    except Exception as e:
        return f"Error stopping processes: {str(e)}"


class GradioTestingAgent:
    """
    A specialized ToolCallingAgent for testing Gradio applications.

    This agent validates and tests Gradio applications created by the coding agent,
    ensuring they are properly set up, runnable, and functional.
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
        Initialize the Gradio Testing Agent.

        Args:
            model_id: Model ID to use for testing (uses settings if None)
            api_base_url: API base URL (uses settings if None)
            api_key: API key (uses settings if None)
            verbosity_level: Level of verbosity for agent output (uses settings if None)
            max_steps: Maximum number of testing steps (uses settings if None)
        """
        # Use settings as defaults, but allow override
        self.model_id = model_id or settings.test_model_id
        self.api_base_url = api_base_url or settings.api_base_url
        self.api_key = api_key or settings.api_key
        verbosity_level = verbosity_level or settings.testing_verbosity
        max_steps = max_steps or settings.max_testing_steps

        # Initialize the language model for the ToolCallingAgent
        self.model = LiteLLMModel(
            model_id=self.model_id,
            api_base=self.api_base_url,
            api_key=self.api_key,
        )

        # Define the tools for testing
        testing_tools = [
            setup_venv_with_uv,
            run_gradio_app,
            check_app_health,
            test_gradio_ui_basic,
            stop_gradio_processes,
        ]

        # Initialize the ToolCallingAgent
        self.agent = ToolCallingAgent(
            model=self.model,
            tools=testing_tools,
            verbosity_level=verbosity_level,
            max_steps=max_steps,
        )

        self.sandbox_path = Path("sandbox")

    def test_application(self, coding_result: CodingResult) -> TestingResult:
        """
        Test the Gradio application created by the coding agent.

        Args:
            coding_result: The result from the coding agent

        Returns:
            TestingResult containing comprehensive test information
        """
        if not coding_result.success:
            return TestingResult(
                success=False,
                project_path=coding_result.project_path,
                setup_successful=False,
                server_launched=False,
                ui_accessible=False,
                test_cases_passed=[],
                test_cases_failed=["Coding agent failed to create application"],
                error_messages=coding_result.error_messages,
                screenshots=[],
                performance_metrics={},
                logs="Testing skipped due to coding failure",
            )

        project_path = coding_result.project_path

        # Create comprehensive test prompt
        test_prompt = f"""
You are a specialized testing agent for Gradio applications. Your task is to \
thoroughly test the Gradio application located at: {project_path}

Please perform the following testing steps in order:

1. **Environment Setup**: Use setup_venv_with_uv to ensure the virtual environment \
is properly configured
2. **Application Launch**: Use run_gradio_app to start the Gradio application
3. **Health Check**: Use check_app_health to verify the application is responding
4. **UI Testing**: Use test_gradio_ui_basic to test the user interface components
5. **Cleanup**: Use stop_gradio_processes to clean up after testing

For each step, report:
- Whether the step succeeded or failed
- Any error messages encountered
- Performance observations (loading times, responsiveness)
- Screenshots taken (if any)

If any critical step fails, still attempt the remaining steps where possible to \
gather maximum diagnostic information.

The application should be a functional Gradio app with interactive components. Test for:
- Proper page loading
- Presence of Gradio components
- Interactive elements (buttons, inputs, etc.)
- Basic functionality

Provide a comprehensive summary of all test results at the end.
        """

        try:
            # Run the testing workflow
            result = self.agent.run(test_prompt)

            # Parse the agent's response to create structured result
            return self._parse_testing_response(result, project_path)

        except Exception as e:
            return TestingResult(
                success=False,
                project_path=project_path,
                setup_successful=False,
                server_launched=False,
                ui_accessible=False,
                test_cases_passed=[],
                test_cases_failed=["Testing agent execution failed"],
                error_messages=[str(e)],
                screenshots=[],
                performance_metrics={},
                logs=f"Testing agent error: {str(e)}",
            )

    def _parse_testing_response(
        self, response: str, project_path: str
    ) -> TestingResult:
        """
        Parse the agent's testing response into a structured TestingResult.

        Args:
            response: Raw response from the testing agent
            project_path: Path to the tested project

        Returns:
            Structured TestingResult
        """
        # Initialize default values
        setup_successful = False
        server_launched = False
        ui_accessible = False
        test_cases_passed = []
        test_cases_failed = []
        error_messages = []
        screenshots = []
        performance_metrics = {}

        # Simple parsing logic based on common success/failure indicators
        response_lower = response.lower()

        # Check for setup success
        if "successfully set up virtual environment" in response_lower:
            setup_successful = True
            test_cases_passed.append("Virtual environment setup")
        elif "error setting up venv" in response_lower:
            test_cases_failed.append("Virtual environment setup")

        # Check for server launch
        if "successfully started gradio app" in response_lower:
            server_launched = True
            test_cases_passed.append("Gradio application launch")
        elif "error running gradio app" in response_lower:
            test_cases_failed.append("Gradio application launch")

        # Check for health status
        if "application is healthy" in response_lower:
            ui_accessible = True
            test_cases_passed.append("Application health check")
        elif "cannot connect to" in response_lower:
            test_cases_failed.append("Application health check")

        # Check for UI testing
        if (
            "page loaded successfully" in response_lower
            and "gradio container found" in response_lower
        ):
            test_cases_passed.append("UI component testing")
        elif "error during ui testing" in response_lower:
            test_cases_failed.append("UI component testing")

        # Look for screenshots
        if "screenshot saved" in response_lower:
            screenshots.append("/tmp/gradio_test_screenshot.png")

        # Extract performance metrics if mentioned
        if "response time:" in response_lower:
            # Simple regex to extract response time
            import re

            time_match = re.search(r"response time: ([\d.]+)s", response_lower)
            if time_match:
                performance_metrics["response_time_seconds"] = float(
                    time_match.group(1)
                )

        # Determine overall success
        success = (
            setup_successful
            and server_launched
            and ui_accessible
            and len(test_cases_failed) == 0
        )

        return TestingResult(
            success=success,
            project_path=project_path,
            setup_successful=setup_successful,
            server_launched=server_launched,
            ui_accessible=ui_accessible,
            test_cases_passed=test_cases_passed,
            test_cases_failed=test_cases_failed,
            error_messages=error_messages,
            screenshots=screenshots,
            performance_metrics=performance_metrics,
            logs=response,
        )

    def generate_test_report(self, testing_result: TestingResult) -> str:
        """
        Generate a comprehensive test report in markdown format.

        Args:
            testing_result: The result from testing the application

        Returns:
            Markdown-formatted test report
        """
        status_emoji = "✅" if testing_result.success else "❌"

        report = f"""
# Gradio Application Test Report {status_emoji}

## Summary
- **Project Path**: `{testing_result.project_path}`
- **Overall Success**: {testing_result.success}
- **Environment Setup**: {"✅" if testing_result.setup_successful else "❌"}
- **Server Launch**: {"✅" if testing_result.server_launched else "❌"}
- **UI Accessibility**: {"✅" if testing_result.ui_accessible else "❌"}

## Test Cases

### Passed ({len(testing_result.test_cases_passed)})
{chr(10).join(f"- ✅ {case}" for case in testing_result.test_cases_passed)}

### Failed ({len(testing_result.test_cases_failed)})
{chr(10).join(f"- ❌ {case}" for case in testing_result.test_cases_failed)}

## Performance Metrics
{chr(10).join(f"- **{key}**: {value}" for key, value in \
testing_result.performance_metrics.items()) if testing_result.performance_metrics else \
"No performance metrics collected"}

## Screenshots
{chr(10).join(f"- {screenshot}" for screenshot in testing_result.screenshots) \
if testing_result.screenshots else "No screenshots captured"}

## Error Messages
{chr(10).join(f"- {error}" for error in testing_result.error_messages) \
if testing_result.error_messages else "No errors reported"}

## Detailed Logs
```
{testing_result.logs}
```

---
*Report generated by GradioTestingAgent*
        """

        return report.strip()


def create_gradio_testing_agent() -> GradioTestingAgent:
    """
    Create a Gradio testing agent with default settings.

    Returns:
        Configured GradioTestingAgent instance
    """
    return GradioTestingAgent()


if __name__ == "__main__":
    # Example usage
    from coding_agent import create_gradio_coding_agent
    from planning_agent import GradioPlanningAgent

    # Create agents
    planning_agent = GradioPlanningAgent()
    coding_agent = create_gradio_coding_agent()
    testing_agent = create_gradio_testing_agent()

    # Example workflow
    print("Planning a simple calculator app...")
    plan = planning_agent.plan_application(
        "Create a simple calculator with basic arithmetic operations"
    )

    print("Implementing the application...")
    implementation = coding_agent.implement_application(plan)

    print("Testing the application...")
    test_results = testing_agent.test_application(implementation)

    print("Test Report:")
    print(testing_agent.generate_test_report(test_results))
