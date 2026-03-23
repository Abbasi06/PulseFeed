import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import FeedItem, User
from schemas import FeedRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feed", tags=["feed"])

CACHE_TTL_HOURS = 6


def _is_stale(fetched_at: datetime) -> bool:
    age = datetime.now(timezone.utc) - fetched_at.replace(tzinfo=timezone.utc)
    return age > timedelta(hours=CACHE_TTL_HOURS)


def _save_items(items: list[dict], db: Session) -> None:
    for item in items:
        db.add(
            FeedItem(
                user_id=item["user_id"],
                title=item["title"],
                summary=item["summary"],
                source=item["source"],
                url=item["url"],
                topic=item["topic"],
                image_url=item.get("image_url", ""),
                published_date=item.get("published_date", ""),
            )
        )
    db.commit()


@router.get("/{user_id}", response_model=list[FeedRead])
async def get_feed(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[FeedItem]:
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    items = (
        db.query(FeedItem)
        .filter(FeedItem.user_id == user_id)
        .order_by(FeedItem.fetched_at.desc())
        .all()
    )
    if items and not _is_stale(items[0].fetched_at):
        return items

    return await _refresh_feed(user_id, db)


@router.post("/{user_id}/refresh", response_model=list[FeedRead])
async def refresh_feed(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[FeedItem]:
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return await _refresh_feed(user_id, db)


@router.patch("/items/{item_id}/like", response_model=FeedRead)
def toggle_like(
    item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FeedItem:
    item = db.get(FeedItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Feed item not found")
    if item.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    item.liked = not item.liked
    db.commit()
    db.refresh(item)
    return item


async def _refresh_feed(user_id: int, db: Session) -> list[FeedItem]:
    from agents.research_agent import generate_feed

    try:
        items = await generate_feed(user_id, db)
    except Exception as exc:
        logger.error("generate_feed failed for user %d: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail="Feed generation failed") from exc

    db.query(FeedItem).filter(FeedItem.user_id == user_id).delete()
    _save_items(items, db)

    return (
        db.query(FeedItem)
        .filter(FeedItem.user_id == user_id)
        .order_by(FeedItem.fetched_at.desc())
        .all()
    )
