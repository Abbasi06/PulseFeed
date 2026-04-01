import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Event, User
from schemas import EventRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

CACHE_TTL_HOURS = 6
REFRESH_COOLDOWN_SECONDS = 60

_last_refresh: dict[int, float] = {}
_generating: set[int] = set()


def _is_stale(fetched_at: datetime) -> bool:
    age = datetime.now(timezone.utc) - fetched_at.replace(tzinfo=timezone.utc)
    return age > timedelta(hours=CACHE_TTL_HOURS)


def _is_cache_warm(user_id: int, db: Session) -> bool:
    """Return True if the newest event is within the cache TTL."""
    latest_at = (
        db.query(func.max(Event.fetched_at))
        .filter(Event.user_id == user_id)
        .scalar()
    )
    return latest_at is not None and not _is_stale(latest_at)


def _check_cooldown(user_id: int) -> None:
    last = _last_refresh.get(user_id, 0.0)
    elapsed = time.monotonic() - last
    if elapsed < REFRESH_COOLDOWN_SECONDS:
        remaining = int(REFRESH_COOLDOWN_SECONDS - elapsed)
        raise HTTPException(
            status_code=429,
            detail=f"Refresh too soon — wait {remaining}s before trying again",
            headers={"Retry-After": str(remaining)},
        )


def _save_events(evs: list[dict], db: Session) -> None:
    for ev in evs:
        db.add(
            Event(
                user_id=ev["user_id"],
                name=ev["name"],
                date=ev["date"],
                location=ev.get("location", ""),
                type=ev.get("type", ""),
                url=ev.get("url", "#"),
                reason=ev.get("reason", ""),
                image_url=ev.get("image_url", ""),
            )
        )
    db.commit()


@router.get("/{user_id}", response_model=list[EventRead])
async def get_events(
    user_id: int,
    background_tasks: BackgroundTasks,
    response: Response,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Event]:
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    if _is_cache_warm(user_id, db):
        return (
            db.query(Event)
            .filter(Event.user_id == user_id)
            .order_by(Event.fetched_at.desc())
            .all()
        )

    existing = (
        db.query(Event)
        .filter(Event.user_id == user_id)
        .order_by(Event.fetched_at.desc())
        .all()
    )
    response.headers["X-Events-Generating"] = "true"
    return existing


@router.post("/{user_id}/refresh", response_model=list[EventRead])
async def refresh_events(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Event]:
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    _check_cooldown(user_id)
    _last_refresh[user_id] = time.monotonic()
    logger.info("Generator pool supplies events — returning cached for user %d", user_id)
    return (
        db.query(Event)
        .filter(Event.user_id == user_id)
        .order_by(Event.fetched_at.desc())
        .all()
    )


@router.patch("/items/{item_id}/like", response_model=EventRead)
def toggle_like(
    item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Event:
    ev = db.get(Event, item_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if ev.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    ev.liked = not ev.liked
    db.commit()
    db.refresh(ev)
    return ev
