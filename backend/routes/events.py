import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Event, User
from schemas import EventRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

CACHE_TTL_HOURS = 6


def _is_stale(fetched_at: datetime) -> bool:
    age = datetime.now(timezone.utc) - fetched_at.replace(tzinfo=timezone.utc)
    return age > timedelta(hours=CACHE_TTL_HOURS)


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
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Event]:
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    evs = (
        db.query(Event)
        .filter(Event.user_id == user_id)
        .order_by(Event.fetched_at.desc())
        .all()
    )
    if evs and not _is_stale(evs[0].fetched_at):
        return evs

    return await _refresh_events(user_id, db)


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
    return await _refresh_events(user_id, db)


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


async def _refresh_events(user_id: int, db: Session) -> list[Event]:
    from agents.research_agent import generate_events

    try:
        evs = await generate_events(user_id, db)
    except Exception as exc:
        logger.error("generate_events failed for user %d: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail="Events generation failed") from exc

    db.query(Event).filter(Event.user_id == user_id).delete()
    _save_events(evs, db)

    return (
        db.query(Event)
        .filter(Event.user_id == user_id)
        .order_by(Event.fetched_at.desc())
        .all()
    )
