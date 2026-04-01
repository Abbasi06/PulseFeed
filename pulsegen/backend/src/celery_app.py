"""
Celery application instance and beat schedule for PulseGen.

Two processes from one image:
  celery -A src.celery_app worker  ...  (default Dockerfile CMD)
  celery -A src.celery_app beat    ...  (docker-compose override)
"""

from celery import Celery
from src.config import settings

app = Celery(
    "pulsegen_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks"],
)

app.conf.update(
    # ── Serialization ──────────────────────────────────────────────────────────
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # ── Timezone ───────────────────────────────────────────────────────────────
    timezone="UTC",
    enable_utc=True,
    # ── Worker pool: gevent for I/O-bound connector fetches ────────────────────
    worker_pool="gevent",
    worker_concurrency=8,
    # ── Reliability ───────────────────────────────────────────────────────────
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    # ── Gemini free-tier rate limiting (1500 RPD ≈ ~1 RPM sustained) ──────────
    # Allow bursting but throttle per-task-type to avoid 429s across workers.
    task_annotations={
        "src.tasks.gatekeeper_task": {"rate_limit": "30/m"},
        "src.tasks.extractor_task": {"rate_limit": "20/m"},
    },
    # ── Dead-letter via Redis ─────────────────────────────────────────────────
    task_routes={
        "src.tasks.*": {"queue": "generator"},
    },
    # ── Result expiry ─────────────────────────────────────────────────────────
    result_expires=3600,  # 1 hour
    # ── Beat schedule ─────────────────────────────────────────────────────────
    beat_schedule={
        # Main harvest cycle — intelligent swarm across all sources
        "harvest-all-sources-every-5-min": {
            "task": "src.tasks.harvest_cycle",
            "schedule": 300.0,  # 5 minutes
            "options": {"queue": "generator"},
        },
        # Trend analysis over stored documents
        "run-trend-analysis-every-15-min": {
            "task": "src.tasks.trend_analysis_cycle",
            "schedule": 900.0,  # 15 minutes
            "options": {"queue": "generator"},
        },
        # Prune old momentum data (keep last 30 days)
        "prune-momentum-daily": {
            "task": "src.tasks.prune_momentum_data",
            "schedule": 86400.0,  # 24 hours
            "options": {"queue": "generator"},
        },
    },
)
