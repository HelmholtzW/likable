#!/bin/bash

echo "===== Application Startup at $(date) ====="

# Create necessary directories
mkdir -p /var/run/nginx /var/lib/nginx/body /var/lib/nginx/proxy /var/lib/nginx/fastcgi /var/lib/nginx/uwsgi /var/lib/nginx/scgi /var/log/nginx

# Set proper permissions
chmod 755 /var/run/nginx /var/lib/nginx/* /var/log/nginx

# Start nginx with our configuration
echo "Starting nginx..."
nginx -c /app/nginx.conf -g "daemon off;" &
sleep 2

# Start the main Gradio app
echo "Starting Gradio app on port 7862..."
exec python -u app.py --server-port 7862 --server-name 0.0.0.0
