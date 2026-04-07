"""
PulseFeed — Main Application
-----------------------------
User-facing service: auth, profiles, feed, events, briefs.
Runs on port 8000.

The content pipeline (harvesting, gatekeeper, extractor, trend analysis) lives
in a SEPARATE process: PulseGen (pulsegen/backend, port 8001).
This service reads from the shared PostgreSQL database but never writes to generator_documents.

Startup
-------
    cd pulsefeed/backend
    uv run uvicorn main:app --reload --port 8000
"""
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import redis.asyncio as aioredis
import sqlalchemy
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# Load .env — service dir first, then repo root as fallback (neither overrides already-set vars)
_service_env = Path(__file__).parent / ".env"
_root_env = Path(__file__).parents[2] / ".env"
load_dotenv(_service_env)
load_dotenv(_root_env)

from database import Base, engine  # noqa: E402
from routes import events, feed, feed_v2, users  # noqa: E402
from security import AuditMiddleware, SecurityHeadersMiddleware  # noqa: E402


def _run_migrations() -> None:
    """Apply schema additions that are safe to run on every startup (PostgreSQL)."""
    migrations = [
        "ALTER TABLE feed_items ADD COLUMN IF NOT EXISTS image_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE feed_items ADD COLUMN IF NOT EXISTS published_date TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE feed_items ADD COLUMN IF NOT EXISTS liked BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE feed_items ADD COLUMN IF NOT EXISTS disliked BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE feed_items ADD COLUMN IF NOT EXISTS saved BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE feed_items ADD COLUMN IF NOT EXISTS read_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS image_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS liked BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_formats TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS field TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS sub_fields TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS refresh_interval_hours INTEGER NOT NULL DEFAULT 6",
        (
            "CREATE TABLE IF NOT EXISTS feed_briefs ("
            "id SERIAL PRIMARY KEY, "
            "user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE, "
            "headline TEXT NOT NULL DEFAULT '', "
            "signals TEXT NOT NULL DEFAULT '[]', "
            "top_reads TEXT NOT NULL DEFAULT '[]', "
            "watch TEXT NOT NULL DEFAULT '[]', "
            "generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
        ),
        # Performance indexes — safe to re-run (IF NOT EXISTS)
        "CREATE INDEX IF NOT EXISTS idx_feed_items_user_fetched ON feed_items(user_id, fetched_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_events_user_fetched ON events(user_id, fetched_at DESC)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            conn.execute(sqlalchemy.text(sql))
            conn.commit()


def _batch_repersonalize() -> None:
    """
    Every 5 minutes: re-personalize feeds for users whose cached feed is stale.
    Staleness is determined per-user by their refresh_interval_hours setting (3 or 6 hrs).
    Uses PostgreSQL FTS matching only — no external LLM calls.
    Skips users if generator pool has no matches.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.orm import Session

    from agents.feed_personalizer import personalize_feed_sync
    from models import FeedBrief, FeedItem, User
    from routes.feed import _save_items

    now = datetime.now(timezone.utc)
    db = Session(engine)
    try:
        users: list[User] = db.query(User).all()  # type: ignore[assignment]
        stale_user_ids: list[int] = []

        for user in users:
            ttl_hours = int(getattr(user, "refresh_interval_hours", 6))
            cutoff = now - timedelta(hours=ttl_hours)
            latest_at = (
                db.query(FeedItem.fetched_at)
                .filter(FeedItem.user_id == user.id)
                .order_by(FeedItem.fetched_at.desc())  # type: ignore[attr-defined]
                .limit(1)
                .scalar()
            )
            if latest_at is None or latest_at.replace(tzinfo=timezone.utc) < cutoff:
                stale_user_ids.append(user.id)

        if not stale_user_ids:
            return

        logger.info("Batch repersonalize: %d stale users", len(stale_user_ids))
        for user_id in stale_user_ids:
            items = personalize_feed_sync(user_id)
            if not items:
                continue
            db.query(FeedItem).filter(FeedItem.user_id == user_id).delete()
            db.query(FeedBrief).filter(FeedBrief.user_id == user_id).delete()
            _save_items(items, db)
            logger.info("Batch repersonalized user %d: %d items", user_id, len(items))
    except Exception as exc:
        logger.error("Batch repersonalize failed: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    _run_migrations()

    if not os.environ.get("LLM_LIGHT_URL"):
        logger.warning(
            "LLM_LIGHT_URL is not set — defaulting to http://host.docker.internal:8080/v1; "
            "ensure llama.cpp light server (gemma3-1b) is running on port 8080"
        )

    # Redis for rate limiting — fail-open if unavailable
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_client: Any = None
    try:
        redis_client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await redis_client.ping()
        logger.info("Redis connected at %s — rate limiting active", redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — rate limiting is disabled", exc)
        redis_client = None
    app.state.redis = redis_client

    scheduler = BackgroundScheduler(job_defaults={"misfire_grace_time": 60})
    scheduler.add_job(
        _batch_repersonalize,
        "interval",
        minutes=5,
        id="feed_repersonalize",
        max_instances=1,
    )
    scheduler.start()

    yield

    if redis_client is not None:
        await redis_client.aclose()
    scheduler.shutdown(wait=False)


app = FastAPI(title="PulseFeed API", lifespan=lifespan)

_ALLOWED_ORIGINS = [
    # local dev — Vite (5173-5182) + production frontend (3000)
    "http://localhost:3000",
    *[f"http://localhost:{p}" for p in range(5173, 5183)],
    # production — set ALLOWED_ORIGIN env var to your domain
    *([o.strip() for o in os.environ["ALLOWED_ORIGIN"].split(",")]
      if os.environ.get("ALLOWED_ORIGIN") else []),
]

# Middleware stack — registered innermost-first; last add_middleware = outermost.
# Request flow:  SecurityHeaders → Audit → CORS → Router
# Response flow: Router → CORS → Audit (log 4xx) → SecurityHeaders (add headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Feed-Generating", "X-Events-Generating", "Retry-After"],
)
app.add_middleware(AuditMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(users.router)
app.include_router(feed.router)
app.include_router(events.router)
app.include_router(feed_v2.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pulsefeed"}
