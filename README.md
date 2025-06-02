# 💗 Likable

A Gradio application builder powered by Smolagents CodeAgent for intelligent planning.

## Features

- **AI-Powered Planning**: Uses Smolagents CodeAgent to create comprehensive plans for Gradio applications
- **Interactive Chat Interface**: Describe what you want to build in natural language
- **Structured Planning Output**: Get detailed action plans, implementation strategies, and testing approaches
- **Component Analysis**: Automatically identifies required Gradio components and dependencies
- **Preview & Code Views**: Switch between live preview and generated code
- **Environment-based Configuration**: Flexible configuration via environment variables

## Setup

1. **Install dependencies:**
   ```bash
   uv install
   ```

2. **Configure environment variables:**
   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env with your configuration
   # At minimum, set your API_KEY
   ```

3. **Set up your API_KEY:**

   Add it to your `.env` file:
   ```
   API_KEY=your_actual_key_here
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

## Configuration

The application uses environment variables for configuration. See `.env.example` for all available options:

### Core Configuration
- `API_KEY`: Your API key (required)
- `MODEL_ID`: Model to use for planning (default: Qwen/Qwen2.5-Coder-32B-Instruct)

### Application Settings
- `GRADIO_HOST`: Host to bind Gradio server (default: 127.0.0.1)
- `GRADIO_PORT`: Port for Gradio server (default: 7860)
- `GRADIO_DEBUG`: Enable debug mode (default: true)

### Planning Agent Settings
- `PLANNING_VERBOSITY`: Agent verbosity level 0-2 (default: 1)
- `MAX_PLANNING_STEPS`: Maximum planning steps (default: 10)

### Test Your Configuration
```bash
# View current configuration
python settings.py

# Test the planning agent
python test_planning_agent.py

# Interactive demo
python test_planning_agent.py demo
```

## Planning Agent

The core of Likable is the `GradioPlanningAgent` which uses Smolagents to:

- Analyze your application requirements
- Create detailed action plans
- Suggest appropriate Gradio components
- Plan implementation strategies
- Design testing approaches
- Estimate complexity and dependencies

### Using the Planning Agent Directly

```python
from planning_agent import GradioPlanningAgent

# Uses configuration from settings.py (loads from .env)
agent = GradioPlanningAgent()
result = agent.plan_application("Create a simple calculator app")

print(agent.format_plan_as_markdown(result))
```

## Project Structure

```
likable/
├── app.py                 # Main Gradio application
├── planning_agent.py      # Smolagents CodeAgent for planning
├── settings.py            # Configuration management
├── test_planning_agent.py # Test script and examples
├── .env.example           # Environment variables template
├── pyproject.toml         # Project dependencies
└── README.md              # This file
```

## Environment Requirements

- Python 3.12+
- Inference API key
- Internet connection for model inference

## Dependencies

- `gradio` - Web UI framework
- `smolagents` - AI agent framework
- `python-dotenv` - Environment variable management

---

*Built with ❤️ using Gradio and Smolagents*
