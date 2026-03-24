import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import sqlalchemy.exc
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# Load .env from project root regardless of working directory
load_dotenv(Path(__file__).parent.parent / ".env")

from database import Base, engine  # noqa: E402
from routes import events, feed, users  # noqa: E402


def _run_migrations() -> None:
    """Add columns introduced after initial schema creation."""
    migrations = [
        "ALTER TABLE feed_items ADD COLUMN image_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE feed_items ADD COLUMN published_date TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE feed_items ADD COLUMN liked INTEGER NOT NULL DEFAULT 0",
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning(
            "GEMINI_API_KEY is not set — feed generation will fail on first request"
        )
    yield


app = FastAPI(title="PulseBoard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://localhost:5179",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(feed.router)
app.include_router(events.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
