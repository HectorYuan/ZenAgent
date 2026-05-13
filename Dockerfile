# ZenAgent Docker Image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml setup.py ./
COPY packages/ ./packages/
COPY tests/ ./tests/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 zenagent && chown -R zenagent:zenagent /app
USER zenagent

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "-m", "zenagent", "serve"]
