# ── Stage 1: dependency resolver ─────────────────────────────────────────────
FROM python:3.13-slim AS builder

RUN pip install uv
WORKDIR /build
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Source only — no frontend, no FastAPI serving layer
COPY src/ ./src/

# Non-root security
RUN useradd -m -u 1001 worker
USER worker

# Celery worker health probe
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD celery -A src.celery_app inspect ping -d "celery@$HOSTNAME" || exit 1

# Default: run the task worker.
# Override CMD in compose to run beat scheduler.
CMD ["celery", "-A", "src.celery_app", "worker", \
     "--loglevel=info", "--queues=generator", \
     "--concurrency=8", "--pool=gevent"]
