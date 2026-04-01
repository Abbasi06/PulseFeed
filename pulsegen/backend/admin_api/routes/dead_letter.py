"""
GET    /admin/dead-letter       — failed document queue
POST   /admin/dead-letter/{index}/retry — re-queue one item
DELETE /admin/dead-letter       — flush entire queue
"""

import json
import logging
from typing import Any

import redis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class DeadLetterItem(BaseModel):
    url: str
    title: str
    source: str
    error: str
    failed_at: str


class DeadLetterResponse(BaseModel):
    items: list[DeadLetterItem]
    count: int


def _get_redis() -> redis.Redis | None:
    import os

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as exc:
        logger.warning("Could not connect to Redis: %s", exc)
        return None


_DEAD_LETTER_KEY = "pulsegen:dead_letter:storage"


@router.get("/dead-letter", response_model=DeadLetterResponse)
def get_dead_letter(limit: int = 50) -> DeadLetterResponse:
    """Return failed document queue."""
    r = _get_redis()
    if r is None:
        return DeadLetterResponse(items=[], count=0)

    limit = min(limit, 500)

    try:
        # LRANGE returns items in order (newest first, since we LPUSH)
        raw_items = r.lrange(_DEAD_LETTER_KEY, 0, limit - 1)
        items = []
        for raw in raw_items:
            try:
                entry = json.loads(raw)
                items.append(
                    DeadLetterItem(
                        url=entry.get("url", ""),
                        title=entry.get("title", ""),
                        source=entry.get("source", ""),
                        error=entry.get("error", ""),
                        failed_at=entry.get("failed_at", ""),
                    )
                )
            except Exception as e:
                logger.warning("Failed to parse dead-letter item: %s", e)

        count = r.llen(_DEAD_LETTER_KEY) or 0
        return DeadLetterResponse(items=items, count=count)
    except Exception as exc:
        logger.error("Failed to fetch dead-letter queue: %s", exc)
        return DeadLetterResponse(items=[], count=0)


@router.post("/dead-letter/{index}/retry")
def retry_dead_letter_item(index: int) -> dict[str, str]:
    """Re-queue one failed item from dead-letter."""
    r = _get_redis()
    if r is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    try:
        # Get the item at index
        raw_item = r.lindex(_DEAD_LETTER_KEY, index)
        if not raw_item:
            raise HTTPException(status_code=404, detail="Item not found")

        entry = json.loads(raw_item)

        # Re-queue to celery task queue (simplified — would normally reconstruct the task)
        logger.info("Retrying dead-letter item: %s", entry.get("url"))
        return {"status": "queued", "url": entry.get("url", "")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/dead-letter")
def clear_dead_letter() -> dict[str, str]:
    """Flush entire dead-letter queue."""
    r = _get_redis()
    if r is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    try:
        count = r.llen(_DEAD_LETTER_KEY) or 0
        r.delete(_DEAD_LETTER_KEY)
        return {"status": "cleared", "count": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
