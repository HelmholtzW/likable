---
title: Likable GitHub
emoji: 💗
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
---

# 💗 Likable GitHub

A powerful AI coding assistant that can create and preview Gradio applications in real-time.

## Features

- **Real-time Code Generation**: AI agent that can write and modify code
- **Live Preview**: See your applications running instantly in an iframe
- **Multiple AI Providers**: Support for Anthropic, OpenAI, Mistral, and more
- **File Management**: Edit and save files directly in the interface
- **API Key Management**: Secure configuration for different AI providers

## Usage

1. Configure your API keys in the Settings tab
2. Ask the AI to create or modify applications
3. View the live preview in the Preview tab
4. Edit code directly in the Code tab

## Architecture

This Space uses nginx as a reverse proxy to serve both the main application and preview applications on a single port, making it compatible with Hugging Face Spaces' single-port limitation.
