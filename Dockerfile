FROM python:3.9-slim

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

# Expose port 7860 (required by HF Spaces)
EXPOSE 7860

# Run the main application using the 'gradio' command
CMD ["gradio", "app.py", "--server_name", "0.0.0.0", "--server_port", "7860"]
