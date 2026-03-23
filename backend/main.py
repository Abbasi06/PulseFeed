from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from project root regardless of working directory
load_dotenv(Path(__file__).parent.parent / ".env")

from database import Base, engine
from routes import events, feed, users


def _run_migrations() -> None:
    """Add columns introduced after initial schema creation."""
    migrations = [
        "ALTER TABLE feed_items ADD COLUMN image_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE feed_items ADD COLUMN published_date TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE feed_items ADD COLUMN liked INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN image_url TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE events ADD COLUMN liked INTEGER NOT NULL DEFAULT 0",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(__import__("sqlalchemy").text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    yield


app = FastAPI(title="PulseBoard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
