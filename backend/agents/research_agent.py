"""
Agentic research pipeline for PulseBoard.

Two entry points:
  generate_feed(user_id, db)   -> list of validated FeedItem dicts
  generate_events(user_id, db) -> list of validated Event dicts

Both are async; DDGS searches run in a thread-pool executor so they don't
block the event loop. The news and events pipelines run in parallel when
called via asyncio.gather() (see the __main__ block for an example).
"""

import asyncio
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Allow running directly: uv run backend/agents/research_agent.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from ddgs import DDGS
from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from database import engine
from models import Base, User

load_dotenv(Path(__file__).parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash-lite"
TODAY = date.today().isoformat()
MAX_FEED = 20
MAX_EVENTS = 10

_FEED_DEFAULTS: dict[str, str] = {
    "title": "Untitled",
    "summary": "",
    "source": "Unknown",
    "url": "#",
    "topic": "General",
    "published_date": TODAY,
}

_JSON_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment")
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Search helper
# ---------------------------------------------------------------------------


def search_web(query: str, timelimit: str | None = None) -> list[dict[str, str]]:
    """Return the top 5 DuckDuckGo results for *query*. Never raises."""
    try:
        with DDGS() as ddgs:
            return ddgs.text(query, max_results=5, timelimit=timelimit) or []
    except Exception as exc:
        logger.warning("search_web failed for %r: %s", query, exc)
        return []


async def _search_all(
    queries: list[str], timelimit: str | None = None
) -> list[dict[str, str]]:
    """Run all queries in parallel via the default thread-pool executor."""
    loop = asyncio.get_running_loop()
    result_batches: list[list[dict[str, str]]] = await asyncio.gather(
        *[loop.run_in_executor(None, search_web, q, timelimit) for q in queries]
    )
    return [item for batch in result_batches for item in batch]


async def _gemini(client: genai.Client, contents: str) -> str:
    """Run a synchronous Gemini call in a thread so it doesn't block the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=_JSON_CONFIG,
        ).text or "",
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_feed_items(
    raw: list[dict[str, object]], user_id: int
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for item in raw:
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if not title and not summary:
            logger.warning("Discarding feed item — both title and summary are empty")
            continue
        out.append(
            {
                "user_id": user_id,
                "title": title or _FEED_DEFAULTS["title"],
                "summary": summary,
                "source": str(item.get("source") or _FEED_DEFAULTS["source"]),
                "url": str(item.get("url") or _FEED_DEFAULTS["url"]),
                "topic": str(item.get("topic") or _FEED_DEFAULTS["topic"]),
                "published_date": str(
                    item.get("published_date") or _FEED_DEFAULTS["published_date"]
                ),
            }
        )
    return out[:MAX_FEED]


def _validate_events(
    raw: list[dict[str, object]], user_id: int
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for item in raw:
        if not item.get("name") or not item.get("date"):
            logger.warning("Discarding event — missing name or date")
            continue
        out.append(
            {
                "user_id": user_id,
                "name": str(item["name"]),
                "date": str(item["date"]),
                "location": str(item.get("location") or ""),
                "type": str(item.get("type") or ""),
                "url": str(item.get("url") or "#"),
                "reason": str(item.get("reason") or ""),
            }
        )
    return out[:MAX_EVENTS]


# ---------------------------------------------------------------------------
# Feed pipeline
# ---------------------------------------------------------------------------


def _build_profile(user: User) -> str:
    parts = [
        f"Occupation: {user.occupation}",
        f"Interests: {', '.join(user.interests)}",
    ]
    if user.hobbies:
        parts.append(f"Hobbies: {', '.join(user.hobbies)}")
    return "\n".join(parts)


def _build_feed_queries(user: User) -> list[str]:
    """Build search queries from user profile without using an LLM call."""
    queries = [f"{user.occupation} latest news {TODAY[:4]}"]
    for interest in user.interests[:2]:
        queries.append(f"{interest} news research {TODAY[:4]}")
    return queries


def _build_event_queries(user: User) -> list[str]:
    """Build event search queries from user profile without using an LLM call."""
    queries = [f"{user.occupation} conference {TODAY[:4]}"]
    for interest in user.interests[:2]:
        queries.append(f"{interest} meetup conference {TODAY[:4]}")
    return queries


async def generate_feed(
    user_id: int, db: Session
) -> list[dict[str, object]]:
    """Search the web and use Gemini to summarize news for *user_id*."""
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    client = _get_client()
    profile = _build_profile(user)

    # Step 1: build queries programmatically (no LLM call needed)
    queries = _build_feed_queries(user)
    logger.info("Feed queries for user %d: %s", user_id, queries)

    # Step 2: run searches in parallel — limit to yesterday's news
    raw_results = await _search_all(queries, timelimit="d")

    if not raw_results:
        logger.warning("No search results for user %d — returning placeholder", user_id)
        return [
            {
                "user_id": user_id,
                "title": "No new updates found",
                "summary": "No search results were available at this time.",
                "source": "Unknown",
                "url": "#",
                "topic": "General",
                "published_date": TODAY,
            }
        ]

    # Step 3: one Gemini call to summarize into structured feed items
    text = await _gemini(
        client,
        f"You are curating a personalized knowledge feed for:\n{profile}\n\n"
        f"Today is {TODAY}. From the raw search results below, select the most "
        f"relevant items and summarize each in 2-3 sentences.\n\n"
        f"Raw results:\n{json.dumps(raw_results, indent=2)}\n\n"
        f"Return a JSON array of objects with exactly these keys: "
        f"title, summary, source, url, topic, published_date. "
        f"Return between 5 and {MAX_FEED} items.",
    )
    raw_items: list[dict[str, object]] = json.loads(text)
    return _validate_feed_items(raw_items, user_id)


# ---------------------------------------------------------------------------
# Events pipeline
# ---------------------------------------------------------------------------


async def generate_events(
    user_id: int, db: Session
) -> list[dict[str, object]]:
    """Search the web and use Gemini to extract upcoming events for *user_id*."""
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    client = _get_client()
    profile = _build_profile(user)

    # Step 1: build queries programmatically (no LLM call needed)
    queries = _build_event_queries(user)
    logger.info("Event queries for user %d: %s", user_id, queries)

    # Step 2: run searches in parallel — last week to capture upcoming event announcements
    raw_results = await _search_all(queries, timelimit="w")

    if not raw_results:
        logger.warning("No event results for user %d", user_id)
        return []

    # Step 3: one Gemini call to extract structured events
    text = await _gemini(
        client,
        f"You are finding upcoming events for:\n{profile}\n\n"
        f"Today is {TODAY}. From the raw search results below, extract relevant "
        f"2026 conferences, meetups, workshops, and events. "
        f"Only include events with a known name and date.\n\n"
        f"Raw results:\n{json.dumps(raw_results, indent=2)}\n\n"
        f"Return a JSON array of objects with exactly these keys: "
        f"name, date, location, type, url, reason. "
        f"Return between 3 and {MAX_EVENTS} items.",
    )
    raw_events: list[dict[str, object]] = json.loads(text)
    return _validate_events(raw_events, user_id)


# ---------------------------------------------------------------------------
# Manual test runner
# ---------------------------------------------------------------------------


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    Base.metadata.create_all(bind=engine)

    # Ensure a test user exists
    with Session(engine) as db:
        user = db.get(User, 1)
        if user is None:
            user = User(
                name="Test User",
                occupation="Software Engineer",
                interests=["AI", "Python", "open source software"],
                hobbies=["reading", "hiking"],
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id

    # Run both pipelines concurrently, each with its own session
    with Session(engine) as feed_db, Session(engine) as events_db:
        feed_items, events = await asyncio.gather(
            generate_feed(user_id, feed_db),
            generate_events(user_id, events_db),
        )

    print("\n=== FEED ITEMS ===")
    print(json.dumps(feed_items, indent=2, default=str))
    print(f"\n({len(feed_items)} items)")

    print("\n=== EVENTS ===")
    print(json.dumps(events, indent=2, default=str))
    print(f"\n({len(events)} items)")


if __name__ == "__main__":
    asyncio.run(_main())
