"""
GET  /admin/pipeline/status — pipeline phase + queue depth
POST /admin/pipeline/run-now — manually trigger harvest_cycle
"""

import logging
import threading
import time
from collections import defaultdict
from typing import cast

import redis
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-process rate limiter: 3 requests per 60 seconds per IP ────────────────
_RATE_LIMIT_MAX = 3
_RATE_LIMIT_WINDOW = 60  # seconds
_request_timestamps: dict[str, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()


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
        queue_depth = cast(int, r.llen("celery")) or 0
        # Could store last_run in Redis as well
        return PipelineStatus(queue_depth=queue_depth, last_run=None)
    except Exception as exc:
        logger.error("Failed to get pipeline status: %s", exc)
        return PipelineStatus(queue_depth=0, last_run=None)


def _check_rate_limit(client_ip: str) -> None:
    """Raise HTTP 429 if this IP has exceeded the run-now rate limit."""
    now = time.monotonic()
    with _rate_lock:
        timestamps = _request_timestamps[client_ip]
        # Remove timestamps outside the current window
        _request_timestamps[client_ip] = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(_request_timestamps[client_ip]) >= _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {_RATE_LIMIT_MAX} requests per {_RATE_LIMIT_WINDOW}s.",
                headers={"Retry-After": str(_RATE_LIMIT_WINDOW)},
            )
        _request_timestamps[client_ip].append(now)


@router.post("/pipeline/run-now", response_model=RunNowResponse)
def run_pipeline_now(request: Request, background_tasks: BackgroundTasks) -> RunNowResponse:
    """Manually trigger a harvest_cycle task."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    from src.celery_app import app as celery_app

    try:
        celery_app.send_task("src.tasks.harvest_cycle")
        return RunNowResponse(accepted=True, message="harvest_cycle queued")
    except Exception as exc:
        logger.error("Failed to queue harvest_cycle: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
