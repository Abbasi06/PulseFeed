"""
GET  /admin/pipeline/status — pipeline phase + queue depth
POST /admin/pipeline/run-now — manually trigger harvest_cycle
"""

import json
import logging
from typing import Any

import redis
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class PipelineStatus(BaseModel):
    queue_depth: int
    last_run: str | None


class RunNowResponse(BaseModel):
    accepted: bool
    message: str


def _get_redis() -> redis.Redis | None:
    import os

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as exc:
        logger.warning("Could not connect to Redis: %s", exc)
        return None


@router.get("/pipeline/status", response_model=PipelineStatus)
def get_pipeline_status() -> PipelineStatus:
    """Return current pipeline queue depth."""
    r = _get_redis()
    if r is None:
        return PipelineStatus(queue_depth=0, last_run=None)

    try:
        queue_depth = r.llen("celery") or 0
        # Could store last_run in Redis as well
        return PipelineStatus(queue_depth=queue_depth, last_run=None)
    except Exception as exc:
        logger.error("Failed to get pipeline status: %s", exc)
        return PipelineStatus(queue_depth=0, last_run=None)


@router.post("/pipeline/run-now", response_model=RunNowResponse)
def run_pipeline_now(background_tasks: BackgroundTasks) -> RunNowResponse:
    """Manually trigger a harvest_cycle task."""
    from src.celery_app import app as celery_app

    try:
        # Fire the task asynchronously
        celery_app.send_task("src.tasks.harvest_cycle")
        return RunNowResponse(accepted=True, message="harvest_cycle queued")
    except Exception as exc:
        logger.error("Failed to queue harvest_cycle: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
