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
from pathlib import Path

from smolagents import LiteLLMModel, ToolCallingAgent, tool

from settings import settings


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
            ["uv", "run", "gradio", "app.py"],
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


@tool
def uv_add_packages(project_path: str, packages: str) -> str:
    """
    Add missing packages to the project using uv add.

    Args:
        project_path: Path to the project directory containing pyproject.toml
        packages: Space-separated list of package names to add \
        (e.g., "requests pandas numpy")

    Returns:
        Status message indicating success or failure of adding packages
    """
    try:
        # Change to project directory
        original_cwd = os.getcwd()
        project_dir = Path(project_path)

        if not project_dir.exists():
            return f"Error: Project directory {project_path} does not exist"

        # Check if pyproject.toml exists
        pyproject_file = project_dir / "pyproject.toml"
        if not pyproject_file.exists():
            return f"Error: pyproject.toml not found in {project_path}"

        os.chdir(project_dir)

        # Split packages and add them one by one for better error handling
        package_list = packages.strip().split()
        if not package_list:
            return "Error: No packages specified to add"

        added_packages = []
        failed_packages = []

        for package in package_list:
            if not package.strip():
                continue

            result = subprocess.run(
                ["uv", "add", package.strip()],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes timeout per package
            )

            if result.returncode == 0:
                added_packages.append(package.strip())
            else:
                failed_packages.append(f"{package.strip()} ({result.stderr.strip()})")

        os.chdir(original_cwd)

        # Prepare status message
        status_parts = []
        if added_packages:
            status_parts.append(f"Successfully added: {', '.join(added_packages)}")
        if failed_packages:
            status_parts.append(f"Failed to add: {'; '.join(failed_packages)}")

        if not status_parts:
            return "No packages were processed"

        return "; ".join(status_parts)

    except subprocess.TimeoutExpired:
        os.chdir(original_cwd)
        return f"Error: uv add timed out while adding packages: {packages}"
    except FileNotFoundError:
        os.chdir(original_cwd)
        return "Error: uv command not found. Please install uv first."
    except Exception as e:
        os.chdir(original_cwd)
        return f"Unexpected error adding packages: {str(e)}"


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
        self.name = "testing_agent"
        self.description = """Expert QA engineer specializing in Gradio application \
testing and validation.

This agent thoroughly tests Gradio applications by:
- Setting up virtual environments using uv
- Launching and health-checking Gradio applications
- Performing basic UI testing with browser automation
- Validating functionality and responsiveness
- Generating comprehensive test reports with screenshots
- Providing detailed error analysis and debugging information

Returns structured test results indicating success/failure with specific details \
about what works and what needs fixing."""

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
            run_gradio_app,
            check_app_health,
            test_gradio_ui_basic,
            stop_gradio_processes,
            uv_add_packages,
        ]

        # Initialize the ToolCallingAgent
        self.agent = ToolCallingAgent(
            model=self.model,
            tools=testing_tools,
            verbosity_level=verbosity_level,
            max_steps=max_steps,
            name=self.name,
            description=self.description,
        )

        self.sandbox_path = Path("sandbox")

    def __call__(self, task: str, **kwargs) -> str:
        """
        Handle testing tasks as a managed agent.

        Args:
            task: The coding result or task description
            **kwargs: Additional keyword arguments (ignored)

        Returns:
            String response containing the formatted testing result
        """
        full_prompt = f"""You are an expert QA engineer specializing in \
Gradio application testing and validation.

**CONTEXT:**
You received this message from an expert Python developer:
```
{task}
```

**YOUR MISSION:**
Perform comprehensive testing of the Gradio application and provide a detailed \
quality assurance report.

**TESTING PROTOCOL:**
1. **Application Launch**: Use `run_gradio_app` to start the application
2. **Dependency Management**: If missing packages are detected, use `uv_add_packages` \
to add them
3. **Health Check**: Use `check_app_health` to verify HTTP response
4. **UI Testing**: Use `test_gradio_ui_basic` for basic interface validation
5. **Cleanup**: Use `stop_gradio_processes` to clean up after testing

**IMPORTANT CONSTRAINTS:**
- You can ONLY access files in the `./sandbox/` directory
- All projects to test will be located in subdirectories of `./sandbox/`
- Use relative paths starting with `./sandbox/[project_name]`

**REPORT FORMAT:**
Structure your final report as follows:

## 🧪 GRADIO APPLICATION TEST REPORT

### 📋 Test Summary
- **Application**: [App name/purpose]
- **Test Status**: ✅ PASSED / ❌ FAILED / ⚠️ PARTIAL
- **Test Duration**: [Time taken]
- **Key Findings**: [Brief summary]

### 🔧 Environment Setup
- **Virtual Environment**: [Status and details]
- **Dependencies**: [Installation results]
- **Setup Issues**: [Any problems encountered]

### 🚀 Application Launch
- **Startup Status**: [Success/failure]
- **Server URL**: [Access URL if successful]
- **Launch Time**: [Time to start]
- **Startup Logs**: [Relevant output]

### 🏥 Health Check
- **HTTP Response**: [Status code and response time]
- **Accessibility**: [Can the app be reached]
- **Performance**: [Response times, any issues]

### 🖥️ User Interface Testing
- **Page Load**: [Success/failure]
- **Gradio Container**: [Found/not found]
- **Interactive Elements**: [Count and types]
- **UI Responsiveness**: [Any issues]
- **Screenshots**: [Paths to saved images]

### ⚠️ Issues Found
- [List any problems, bugs, or concerns]
- [Include severity levels: CRITICAL, HIGH, MEDIUM, LOW]
- [Provide specific error messages and context]

### ✅ Recommendations
- [Suggestions for improvements]
- [Required fixes for critical issues]
- [Performance optimization suggestions]

### 📊 Test Metrics
- **Total Tests**: [Number]
- **Passed**: [Number]
- **Failed**: [Number]
- **Success Rate**: [Percentage]

**TESTING GUIDELINES:**
- Always clean up processes after testing
- Capture screenshots when possible for documentation
- Report specific error messages, not just generic failures
- Distinguish between setup issues vs. application issues
- Test both functionality and user experience
- Provide actionable feedback for developers

**ERROR HANDLING:**
- If environment setup fails, provide specific uv/dependency guidance
- If missing packages are detected, use `uv_add_packages` to add them automatically
- If app won't start, analyze logs for root cause and check for import errors
- If UI testing fails, check if it's a browser/selenium issue vs. app issue
- Always attempt cleanup even if earlier steps fail

Begin testing now and provide your comprehensive report."""
        try:
            return self.agent.run(full_prompt)

        except Exception as e:
            return f"❌ Testing failed: {str(e)}"


if __name__ == "__main__":
    # Example usage
    from coding_agent import GradioCodingAgent
    from planning_agent import GradioPlanningAgent

    # Create agents
    planning_agent = GradioPlanningAgent()
    coding_agent = GradioCodingAgent()
    testing_agent = GradioTestingAgent()

    plan_result = planning_agent(
        "Create a simple calculator with basic arithmetic operations /no_think"
    )

    implementation_result = coding_agent(plan_result)

    test_result = testing_agent(implementation_result)

    print("=== TEST REPORT ===")
    print(test_result)
