# ==========================================
# LABOS Backend - Dockerfile
# ==========================================
# Build: docker build -t labos-backend .
# Run:   docker run -p 18800:18800 -v ./data:/data labos-backend
# ==========================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 18800

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:18800/health || exit 1

# Create non-root user
RUN addgroup --system --gid 1001 python && \
    adduser --system --uid 1001 --gid 1001 --home /app python

# Create data directory (will be mounted as volume)
# /data is the container path for sandboxes, logs, etc.
RUN mkdir -p /data/sandboxes /data/logs /app/.cache && \
    chown -R python:python /app /data

# Set environment variables
ENV HOME=/app
ENV USER=python
# Default sandbox path (can be overridden by .env or docker-compose)
ENV SANDBOX_ROOT=/data/sandboxes

# Switch to non-root user
USER python

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18800"]
