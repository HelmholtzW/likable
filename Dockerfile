FROM python:3.12-slim

# Set up a new user named "user" with user ID 1000 (required by HF Spaces)
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Copy requirements and install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application code
COPY --chown=user . .

# Create sandbox directory if it doesn't exist and add a dummy app.py
RUN mkdir -p sandbox && \
    echo 'import gradio as gr; gr.Interface(lambda x: "Preview not available", "text", "text").launch(server_port=7861, server_name="0.0.0.0")' > sandbox/app.py

# Expose port 7860 (the only port HF Spaces allows)
EXPOSE 7860

# Start the main application directly
CMD ["python", "app.py"]
