# Multi-stage Dockerfile for PulseGen microservice
# Supports: Celery worker (runtime), Celery beat (runtime with override), FastAPI admin API (admin_api)

FROM python:3.13-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy pyproject.toml and install Python dependencies
COPY pyproject.toml .
RUN uv pip install --system -e .

# Copy application code
COPY src/ ./src/
COPY mcp_servers/ ./mcp_servers/
COPY admin_api/ ./admin_api/

# ============================================================================
# Runtime target: Celery worker / beat scheduler
# ============================================================================
FROM base AS runtime

# Default: Celery worker with gevent pool
CMD ["celery", "-A", "src.celery_app", "worker", "--pool=gevent", "--concurrency=10", "--loglevel=info"]

# ============================================================================
# Admin API target: FastAPI admin console backend
# ============================================================================
FROM base AS admin_api

EXPOSE 8001

CMD ["uvicorn", "admin_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
