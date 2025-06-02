# 💗Likable
It's almost Lovable - Build Gradio apps, using only a chat interface.

## 🚀 Features

- **Chat Interface**: Natural language conversation with AI to describe what you want to build
- **Live Preview**: See your generated application in real-time
- **Code View**: Toggle to view the generated Python/Gradio code
- **Example Prompts**: Get started quickly with pre-built examples
- **Modern UI**: Clean, responsive interface inspired by Lovable

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- pip or uv for package management

### Installation

Using uv (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python app.py
```

Or use the launcher:
```bash
python run.py
```

The application will be available at `http://localhost:7860`

## 🎯 Usage

1. **Start a Conversation**: Type what you want to build in the chat interface
2. **View Results**: See the generated app preview on the right
3. **Toggle Views**: Switch between "Preview" and "Code" to see the implementation
4. **Iterate**: Continue chatting to refine and improve your application

### Example Prompts
- "Create a simple todo app"
- "Build a calculator interface"
- "Make a weather dashboard"
- "Design a photo gallery"
- "Create a chat interface"

## 🏗️ Architecture

### Components
- **Chat Interface** (Left Panel)
  - AI-powered conversation
  - Example prompts
  - Message history

- **Preview/Code Panel** (Right Panel)
  - Live HTML preview of generated apps
  - Syntax-highlighted code view
  - Toggle between views

### Tech Stack
- **Gradio**: Web UI framework
- **Python**: Backend logic
- **HTML/CSS**: Preview rendering

## 🔮 Roadmap

### Planned Features
- [ ] **Real AI Integration**: Connect to actual LLM APIs
- [ ] **Code Execution**: Run generated code in sandbox (E2B integration)
- [ ] **HuggingFace Deployment**: One-click deployment to HF Spaces  
- [ ] **Advanced Agents**:
  - [ ] Planner Agent (architecture decisions)
  - [ ] Coder Agent (file management, diff editing)
  - [ ] Reviewer Agent (visual testing)
- [ ] **File Management**: 
  - [ ] Read/write/edit files
  - [ ] Project structure management
  - [ ] Git integration
- [ ] **Enhanced Preview**: 
  - [ ] Real Gradio app embedding
  - [ ] Interactive previews
  - [ ] Mobile responsive testing

### Current Status
✅ Basic UI layout  
✅ Chat interface mockup  
✅ Preview/Code toggle  
✅ Example system  
🚧 AI integration (mock responses)  
🚧 Real code generation  
🚧 Live app deployment  

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Inspired by [Lovable](https://lovable.dev/) - the AI-powered web app builder
- Built with [Gradio](https://gradio.app/) - the fastest way to build ML demos
- UI design patterns from modern development tools