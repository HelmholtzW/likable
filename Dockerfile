FROM python:3.12-slim

# Install nginx
RUN apt-get update && apt-get install -y nginx && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -u 1000 user

# Install Python packages globally so they're accessible to all users
WORKDIR /app
COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy nginx configuration as main config
COPY nginx.conf /etc/nginx/nginx.conf

# Create all nginx directories and set permissions for user
RUN mkdir -p /var/run/nginx /var/log/nginx /var/lib/nginx/body /var/lib/nginx/fastcgi \
    /var/lib/nginx/proxy /var/lib/nginx/scgi /var/lib/nginx/uwsgi && \
    chown -R user:user /var/run/nginx /var/log/nginx /var/lib/nginx

# Copy application files and make script executable
COPY --chown=user . /app
RUN chmod +x /app/start.sh

# Switch to user for execution
USER user
ENV PATH="/home/user/.local/bin:$PATH"

CMD ["/app/start.sh"]
