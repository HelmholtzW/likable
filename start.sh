#!/bin/bash

# Start nginx in background as non-root user
echo "Starting nginx..."
nginx -g 'daemon off;' &
NGINX_PID=$!

# Function to handle shutdown
cleanup() {
    echo "Shutting down..."
    kill $NGINX_PID 2>/dev/null
    wait $NGINX_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait a moment for nginx to start
sleep 2

echo "Starting Gradio app on port 7862..."
# Run the main app in foreground so Docker captures its logs
# Use -u flag to disable Python output buffering
python -u app.py --server-port 7862 --server-name 0.0.0.0
