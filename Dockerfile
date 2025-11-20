# Backend Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p agent_outputs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 18800

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:18800/api/system/health || exit 1

# Create non-root user
RUN addgroup --system --gid 1001 python && \
    adduser --system --uid 1001 --group python --home /app

# Create necessary directories and set permissions
RUN mkdir -p /app/.mem0 /app/.cache /app/agent_outputs && \
    chown -R python:python /app

# Set environment variables for user home
ENV HOME=/app
ENV USER=python

# Switch to non-root user
USER python

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18800"]
