"""
PulseFeed — Main Application
-----------------------------
User-facing service: auth, profiles, feed, events, briefs.
Runs on port 8000.

The content pipeline (harvesting, gatekeeper, extractor, trend analysis) lives
in a SEPARATE process: PulseGen (generator_service/main.py, port 8001).
This app reads from generator.db but never writes to it.

Startup
-------
    cd backend
    uv run uvicorn main:app --reload --port 8000
"""
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import sqlalchemy.exc
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# Load .env from project root regardless of working directory
load_dotenv(Path(__file__).parent.parent / ".env")

from database import Base, engine  # noqa: E402
from routes import events, feed, feed_v2, generator_obs, users  # noqa: E402


def _run_migrations() -> None:
    """Add columns introduced after initial schema creation."""
    migrations = [
        "ALTER TABLE feed_items ADD COLUMN image_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE feed_items ADD COLUMN published_date TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE feed_items ADD COLUMN liked INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE feed_items ADD COLUMN disliked INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE feed_items ADD COLUMN saved INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE feed_items ADD COLUMN read_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN image_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE events ADD COLUMN liked INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN preferred_formats TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE users ADD COLUMN field TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE users ADD COLUMN sub_fields TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE users ADD COLUMN preferred_sources TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE users ADD COLUMN followed_creators TEXT NOT NULL DEFAULT '[]'",
        (
            "CREATE TABLE IF NOT EXISTS feed_briefs ("
            "id INTEGER PRIMARY KEY, "
            "user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE, "
            "headline TEXT NOT NULL DEFAULT '', "
            "signals TEXT NOT NULL DEFAULT '[]', "
            "top_reads TEXT NOT NULL DEFAULT '[]', "
            "watch TEXT NOT NULL DEFAULT '[]', "
            "generated_at DATETIME NOT NULL)"
        ),
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(__import__("sqlalchemy").text(sql))
                conn.commit()
            except sqlalchemy.exc.OperationalError:
                pass  # column / table already exists


def _batch_repersonalize() -> None:
    """
    Every 5 minutes: re-personalize feeds for users whose cached feed is
    stale (>30 min old).  Uses FTS5 matching only — no Gemini calls, no
    external network requests.  Skips users if generator.db has no matches.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.orm import Session

    from agents.feed_personalizer import personalize_feed_sync
    from models import FeedBrief, FeedItem, User
    from routes.feed import _save_items

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    db = Session(engine)
    try:
        # Users with a stale or absent feed
        fresh_subq = (
            db.query(FeedItem.user_id)
            .filter(FeedItem.fetched_at >= cutoff)  # type: ignore[operator]
            .distinct()
            .subquery()
        )
        stale_user_ids = [
            row[0]
            for row in db.query(User.id)
            .filter(User.id.notin_(fresh_subq))  # type: ignore[attr-defined, arg-type]
            .all()
        ]
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

    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning(
            "GEMINI_API_KEY is not set — feed generation will fall back to "
            "generator.db pool only; start PulseGen to populate it"
        )

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

    scheduler.shutdown(wait=False)


app = FastAPI(title="PulseFeed API", lifespan=lifespan)

_ALLOWED_ORIGINS = [
    # local dev
    *[f"http://localhost:{p}" for p in range(5173, 5183)],
    # production — set ALLOWED_ORIGIN env var to your Vercel URL, e.g.
    # https://pulseboard.vercel.app
    *([o.strip() for o in os.environ["ALLOWED_ORIGIN"].split(",")]
      if os.environ.get("ALLOWED_ORIGIN") else []),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Feed-Generating", "X-Events-Generating", "Retry-After"],
)

app.include_router(users.router)
app.include_router(feed.router)
app.include_router(events.router)
app.include_router(feed_v2.router)
app.include_router(generator_obs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pulsefeed"}
