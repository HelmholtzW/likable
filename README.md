# 💗 Likable

**AI-powered Gradio app builder that plans and implements complete applications**

Likable is an intelligent development assistant that takes natural language descriptions of applications and turns them into fully functional Gradio apps with proper project structure, dependencies, and documentation.

## ✨ Features

- **🎯 Intelligent Planning**: Uses AI to create comprehensive application plans
- **⚡ Automated Implementation**: Converts plans into working code with proper structure
- **📦 Project Management**: Sets up proper Python projects with `uv` package management
- **🔄 Iterative Development**: Refines implementations until completion
- **🎨 Live Preview**: Real-time preview of generated applications
- **📝 Code Editor**: Built-in code editor for manual adjustments
- **🛠️ Complete Setup**: Handles dependencies, README, and project structure

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- `uv` package manager
- API key for LLM service (HuggingFace, OpenAI, etc.)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/likable.git
   cd likable
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Run the application**:
   ```bash
   uv run python app.py
   ```

5. **Open your browser** to `http://localhost:7860`

## 📋 Environment Variables

Create a `.env` file with the following variables:

```env
# API Configuration for LLM Services
API_KEY=your_api_key_here
API_BASE_URL=  # Optional: for custom LLM services
MODEL_ID=Qwen/Qwen2.5-Coder-32B-Instruct
CODE_MODEL_ID=Qwen/Qwen2.5-Coder-32B-Instruct  # Can be different from planning model

# Gradio Configuration
GRADIO_HOST=127.0.0.1
GRADIO_PORT=7860
GRADIO_DEBUG=false

# Agent Settings
PLANNING_VERBOSITY=1
MAX_PLANNING_STEPS=10
CODING_VERBOSITY=2
MAX_CODING_STEPS=20
```

## 🏗️ Architecture

Likable uses a two-agent system:

### 1. Planning Agent (`planning_agent.py`)
- **Purpose**: Analyzes user requirements and creates comprehensive plans
- **Technology**: Smolagents with LiteLLM integration
- **Output**: Structured planning results with:
  - Action plans
  - Implementation strategies
  - Testing approaches
  - Required Gradio components
  - Dependencies list
  - Complexity estimation

### 2. Coding Agent (`coding_agent.py`)
- **Purpose**: Implements the planned application with proper project structure
- **Technology**: Smolagents CodeAgent with file operations
- **Features**:
  - Sets up `uv` project structure
  - Installs dependencies automatically
  - Creates comprehensive README files
  - Implements all planned features
  - Performs iterative refinement

## 🎯 How It Works

1. **User Input**: Describe your desired application in natural language
2. **Planning Phase**: AI analyzes requirements and creates detailed plans
3. **Implementation Phase**: Coding agent creates complete project structure
4. **Quality Assurance**: Iterative refinement ensures completeness
5. **Deployment Ready**: Generated apps are immediately runnable

## 📁 Project Structure

```
likable/
├── app.py                    # Main Gradio interface
├── planning_agent.py         # AI planning agent
├── coding_agent.py           # AI coding agent
├── settings.py               # Configuration management
├── test_planning_agent.py    # Planning agent tests
├── test_coding_agent.py      # Coding agent tests
├── pyproject.toml           # Project dependencies
├── .env.example             # Environment template
└── sandbox/                 # Generated applications
    └── gradio_app/          # Latest generated app
        ├── app.py           # Main application
        ├── README.md        # Documentation
        └── pyproject.toml   # App dependencies
```

## 🧪 Testing

Run tests to verify functionality:

```bash
# Test planning agent
uv run python test_planning_agent.py

# Test coding agent
uv run python test_coding_agent.py

# Test settings
uv run python settings.py
```

## 🔧 Development

### Adding New Features

1. **Planning Agent Extensions**: Modify `planning_agent.py` to enhance planning capabilities
2. **Coding Agent Tools**: Add new tools to `coding_agent.py` for specialized functionality
3. **UI Improvements**: Update `app.py` for better user experience

### Code Quality

The project uses:
- **Ruff**: Linting and formatting
- **Pre-commit**: Git hooks for quality assurance
- **Type hints**: For better code documentation
- **Docstrings**: Comprehensive documentation

```bash
# Run linting
uv run ruff check

# Format code
uv run ruff format

# Install pre-commit hooks
uv run pre-commit install
```

## 🎨 Example Applications

Likable can create various types of Gradio applications:

- **Text Processing**: Translation, summarization, analysis
- **Image Tools**: Generation, editing, classification
- **Data Applications**: Visualization, analysis, dashboards
- **AI Interfaces**: Chatbots, question-answering systems
- **Utility Apps**: Converters, calculators, tools

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `uv run python -m pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Smolagents**: For the excellent agent framework
- **Gradio**: For the amazing UI framework
- **LiteLLM**: For seamless LLM integration
- **UV**: For fast Python package management

## 🐛 Troubleshooting

### Common Issues

1. **API Key Errors**:
   - Ensure your API key is set in `.env`
   - Check API rate limits and quotas

2. **UV Not Found**:
   ```bash
   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Project Setup Failures**:
   - Ensure you have write permissions in the project directory
   - Check that `uv` is properly installed and accessible

4. **Agent Initialization Issues**:
   - Verify your model ID is correct
   - Check network connectivity for API calls

### Getting Help

- Open an issue on GitHub
- Check the examples in `test_*.py` files
- Review the agent documentation in source code

---

**Happy Building! 🚀**
