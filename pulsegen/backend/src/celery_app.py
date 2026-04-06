"""
Celery application instance and beat schedule for PulseGen.

Two processes from one image:
  celery -A src.celery_app worker  ...  (default Dockerfile CMD)
  celery -A src.celery_app beat    ...  (docker-compose override)

Harvest runs twice daily (06:00 and 18:00 UTC) in batch mode.
llama.cpp servers are only under load during these windows (~minutes),
keeping RAM free the rest of the day.
"""

import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

from src.config import settings

logger = logging.getLogger(__name__)

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
    # ── Worker pool: threads (not gevent) so asyncio.run() works inside tasks ──
    # gevent monkey-patches ThreadPoolExecutor to use greenlets; asyncio.run()
    # raises "cannot be called from a running event loop" inside a greenlet.
    # Threads have no running event loop, so asyncio.run() works correctly.
    worker_pool="threads",
    worker_concurrency=8,
    # ── Reliability ───────────────────────────────────────────────────────────
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    # ── Dead-letter via Redis ─────────────────────────────────────────────────
    task_routes={
        "src.tasks.*": {"queue": "generator"},
    },
    # ── Result expiry ─────────────────────────────────────────────────────────
    result_expires=3600,  # 1 hour
    # ── Beat schedule — batch mode (twice daily) ──────────────────────────────
    beat_schedule={
        # Main harvest: 06:00 and 18:00 UTC
        # llama.cpp servers only needed during these ~10-20 minute windows.
        "harvest-twice-daily": {
            "task": "src.tasks.harvest_cycle",
            "schedule": crontab(hour="6,18", minute="0"),
            "options": {"queue": "generator"},
        },
        # Trend analysis: once daily at 07:00 UTC (after morning harvest settles)
        "trend-analysis-daily": {
            "task": "src.tasks.trend_analysis_cycle",
            "schedule": crontab(hour="7", minute="0"),
            "options": {"queue": "generator"},
        },
        # Prune old momentum data (keep last 30 days)
        "prune-momentum-daily": {
            "task": "src.tasks.prune_momentum_data",
            "schedule": crontab(hour="3", minute="0"),
            "options": {"queue": "generator"},
        },
    },
)


@worker_ready.connect
def _on_worker_ready(sender: object, **kwargs: object) -> None:
    """
    Trigger one harvest_cycle immediately when a worker comes online.

    Uses a short-lived Redis lock (TTL = 5 minutes) so only the first worker
    replica to start fires the initial cycle — not all replicas.
    """
    import redis as redis_lib

    try:
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=3)
        lock_key = "pulsegen:startup_harvest_lock"
        if r.set(lock_key, "1", nx=True, ex=300):
            app.send_task("src.tasks.harvest_cycle", queue="generator")
            logger.info("Worker ready — dispatched startup harvest_cycle")
        else:
            logger.debug("Worker ready — startup harvest already dispatched by another worker")
    except Exception as exc:
        logger.warning("Worker ready — could not dispatch startup harvest: %s", exc)
