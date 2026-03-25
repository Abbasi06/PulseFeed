import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import FeedBrief, FeedItem, User
from schemas import BriefRead, FeedRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feed", tags=["feed"])

CACHE_TTL_HOURS = 6
REFRESH_COOLDOWN_SECONDS = 60

# In-memory cooldown tracker (per-process; acceptable for single-server dev)
_last_refresh: dict[int, float] = {}


def _is_stale(fetched_at: datetime) -> bool:
    age = datetime.now(timezone.utc) - fetched_at.replace(tzinfo=timezone.utc)
    return age > timedelta(hours=CACHE_TTL_HOURS)


def _is_cache_warm(user_id: int, db: Session) -> bool:
    """Return True if the newest feed item is within the cache TTL."""
    latest_at = (
        db.query(func.max(FeedItem.fetched_at))
        .filter(FeedItem.user_id == user_id)
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

    if _is_cache_warm(user_id, db):
        return (
            db.query(FeedItem)
            .filter(FeedItem.user_id == user_id)
            .order_by(FeedItem.fetched_at.desc())
            .all()
        )

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
    _check_cooldown(user_id)
    result = await _refresh_feed(user_id, db)
    _last_refresh[user_id] = time.monotonic()
    return result


@router.get("/{user_id}/brief", response_model=BriefRead)
async def get_brief(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FeedBrief:
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    has_feed = (
        db.query(FeedItem.id).filter(FeedItem.user_id == user_id).limit(1).scalar()
    )
    if not has_feed:
        raise HTTPException(
            status_code=404, detail="No feed items — generate feed first"
        )

    brief = db.query(FeedBrief).filter(FeedBrief.user_id == user_id).first()
    if brief and not _is_stale(brief.generated_at):
        return brief

    return await _refresh_brief(user_id, db)


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


@router.patch("/items/{item_id}/dislike", response_model=FeedRead)
def toggle_dislike(
    item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FeedItem:
    item = db.get(FeedItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Feed item not found")
    if item.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    item.disliked = not item.disliked
    db.commit()
    db.refresh(item)
    return item


@router.patch("/items/{item_id}/save", response_model=FeedRead)
def toggle_save(
    item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FeedItem:
    item = db.get(FeedItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Feed item not found")
    if item.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    item.saved = not item.saved
    db.commit()
    db.refresh(item)
    return item


@router.post("/items/{item_id}/click", response_model=FeedRead)
def record_click(
    item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FeedItem:
    item = db.get(FeedItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Feed item not found")
    if item.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    item.read_count += 1
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
    db.query(FeedBrief).filter(FeedBrief.user_id == user_id).delete()
    _save_items(items, db)

    new_items = (
        db.query(FeedItem)
        .filter(FeedItem.user_id == user_id)
        .order_by(FeedItem.fetched_at.desc())
        .all()
    )
    logger.info("Feed refreshed for user %d: %d items stored", user_id, len(new_items))
    return new_items


async def _refresh_brief(user_id: int, db: Session) -> FeedBrief:
    from agents.research_agent import generate_brief

    try:
        data = await generate_brief(user_id, db)
    except Exception as exc:
        logger.error("generate_brief failed for user %d: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail="Brief generation failed") from exc

    db.query(FeedBrief).filter(FeedBrief.user_id == user_id).delete()
    brief = FeedBrief(
        user_id=user_id,
        headline=str(data.get("headline") or ""),
        signals=data.get("signals") or [],
        top_reads=data.get("top_reads") or [],
        watch=data.get("watch") or [],
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)
    return brief
