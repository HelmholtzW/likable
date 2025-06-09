#!/bin/bash

# Start nginx in background as non-root user
nginx -g 'daemon off;' &
NGINX_PID=$!

# Wait a moment for nginx to start
sleep 2

# Start the main Gradio app on port 7862 (internal)
python app.py --server-port 7862 --server-name 0.0.0.0 &
APP_PID=$!

# Function to handle shutdown
cleanup() {
    echo "Shutting down..."
    kill $NGINX_PID $APP_PID 2>/dev/null
    wait $NGINX_PID $APP_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for any process to exit
wait -n

# If we get here, one process exited, so clean up
cleanup
