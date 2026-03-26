from __future__ import annotations

import os

from celery import Celery
from celery.signals import worker_init

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery(
    "generator",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["generator.tasks"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_annotations={
        "generator.tasks.gatekeeper_task": {"rate_limit": "30/m"},
        "generator.tasks.extractor_task": {"rate_limit": "10/m"},
    },
    task_routes={
        "generator.tasks.harvest_task": {"queue": "ingestion"},
        "generator.tasks.storage_router_task": {"queue": "ingestion"},
        "generator.tasks.gatekeeper_task": {"queue": "llm"},
        "generator.tasks.extractor_task": {"queue": "llm"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@worker_init.connect
def _bootstrap_db(**kwargs: object) -> None:
    """Create generator tables on worker startup — no dependency on the FastAPI app."""
    from .db import init_db
    init_db()
