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
from typing import Any

# Allow running directly: uv run backend/agents/research_agent.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from ddgs import DDGS
from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from database import engine
from models import Base, FeedItem, User

load_dotenv(Path(__file__).parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash-lite"
TODAY = date.today().isoformat()
MAX_FEED = 20
MAX_EVENTS = 10

# Maps preferred_formats values → extra search keywords appended to queries
_FORMAT_SUFFIXES: dict[str, str] = {
    "Research Papers": "research paper arxiv.org",
    "Technical Articles": "article tutorial medium.com dev.to",
    "Books & Guides": "guide book tutorial oreilly",
    "Engineering Blogs": "engineering blog",
}

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


def _parse_json_object(text: str, context: str) -> dict[str, object]:
    """Parse a JSON object from Gemini output, stripping any markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        inner = parts[1] if len(parts) > 1 else ""
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result  # type: ignore[return-value]
        logger.warning("Gemini returned non-dict JSON for %s", context)
        return {}
    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned invalid JSON for %s: %s", context, exc)
        return {}


def _parse_json_list(text: str, context: str) -> list[dict[str, object]]:
    """Parse a JSON array from Gemini output, stripping any markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        inner = parts[1] if len(parts) > 1 else ""
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result  # type: ignore[return-value]
        logger.warning("Gemini returned non-list JSON for %s", context)
        return []
    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned invalid JSON for %s: %s", context, exc)
        return []


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


def _validate_brief(raw: dict[str, object], user_id: int) -> dict[str, Any]:
    """Sanitise and normalise a raw brief dict returned by Gemini."""

    def _to_str_list(val: object, limit: int) -> list[str]:
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()][:limit]
        return []

    raw_top_reads = raw.get("top_reads") or []
    top_reads: list[dict[str, str]] = []
    if isinstance(raw_top_reads, list):
        for item in raw_top_reads[:3]:
            if isinstance(item, dict):
                top_reads.append(
                    {
                        "title": str(item.get("title") or "Untitled"),
                        "url": str(item.get("url") or "#"),
                        "source": str(item.get("source") or "Unknown"),
                    }
                )

    return {
        "user_id": user_id,
        "headline": str(raw.get("headline") or "").strip()[:120],
        "signals": _to_str_list(raw.get("signals"), 5),
        "top_reads": top_reads,
        "watch": _to_str_list(raw.get("watch"), 4),
    }


# ---------------------------------------------------------------------------
# Feed pipeline
# ---------------------------------------------------------------------------


def _build_profile(user: User) -> str:
    parts = [
        f"Occupation: {user.occupation}",
        f"Selected Areas of Focus: {', '.join(user.selected_chips)}",
    ]
    field = getattr(user, "field", "") or ""
    sub_fields: list[str] = getattr(user, "sub_fields", None) or []
    preferred_formats: list[str] = getattr(user, "preferred_formats", None) or []
    if field:
        parts.append(f"Primary Field: {field}")
    if sub_fields:
        parts.append(f"Detailed Focus Areas: {', '.join(sub_fields)}")
    if preferred_formats:
        parts.append(f"Preferred Content Formats: {', '.join(preferred_formats)}")
    return "\n".join(parts)


def _build_feed_queries(user: User) -> list[str]:
    """Build 'Scout' grounded dorking search queries without using an LLM call."""
    queries: list[str] = []

    # Prefer detailed sub_fields over selected_chips for topic queries
    sub_fields: list[str] = getattr(user, "sub_fields", None) or []
    preferred_formats: list[str] = getattr(user, "preferred_formats", None) or []
    focus_items = sub_fields if sub_fields else user.selected_chips

    # Base occupation query
    queries.append(
        f'"{user.occupation}" (news OR breakthrough) {TODAY[:4]}'
        f" site:news.ycombinator.com OR site:arxiv.org OR site:techcrunch.com"
    )

    # Per-topic queries
    for item in focus_items:
        suffix = ""
        for fmt in preferred_formats:
            suffix = _FORMAT_SUFFIXES.get(fmt, "")
            if suffix:
                break
        base = f'"{item}" (latest OR research OR update) {TODAY[:4]}'
        queries.append(f"{base} {suffix}".strip() if suffix else base)

    return queries[:7]


def _build_event_queries(user: User) -> list[str]:
    """Build event search queries using grounded Scout dorking."""
    sub_fields: list[str] = getattr(user, "sub_fields", None) or []
    focus_items = (sub_fields if sub_fields else user.selected_chips)[:3]

    queries = [f'"{user.occupation}" (conference OR summit OR meetup) {TODAY[:4]} -webinar']
    for item in focus_items:
        queries.append(
            f'"{item}" (event OR workshop OR hackathon) {TODAY[:4]}'
            f" site:lu.ma OR site:eventbrite.com OR site:meetup.com"
        )
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
    raw_items = _parse_json_list(text, context=f"feed user={user_id}")
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
    raw_events = _parse_json_list(text, context=f"events user={user_id}")
    return _validate_events(raw_events, user_id)


# ---------------------------------------------------------------------------
# Brief pipeline
# ---------------------------------------------------------------------------


async def generate_brief(user_id: int, db: Session) -> dict[str, Any]:
    """Generate a one-page insight brief from the user's cached feed items."""
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    items = (
        db.query(FeedItem)
        .filter(FeedItem.user_id == user_id)
        .order_by(FeedItem.fetched_at.desc())  # type: ignore[attr-defined]
        .limit(MAX_FEED)
        .all()
    )
    if not items:
        raise ValueError(f"No feed items for user {user_id} — generate feed first")

    client = _get_client()
    profile = _build_profile(user)

    feed_summary = "\n".join(
        f"- [{item.topic}] {item.title}: {item.summary[:200]}" for item in items
    )

    text = await _gemini(
        client,
        f"You are writing a daily insight brief for:\n{profile}\n\n"
        f"Today is {TODAY}. Based on these feed items:\n{feed_summary}\n\n"
        f"Return a JSON object with exactly these keys:\n"
        f"- headline: one punchy sentence capturing today's dominant theme (max 120 chars)\n"
        f"- signals: array of 3-5 short strings, each a key trend or takeaway\n"
        f"- top_reads: array of up to 3 objects with keys title, url, source — "
        f"the highest-value items from the list above\n"
        f"- watch: array of 2-4 short strings — emerging topics or names worth tracking\n"
        f"Return only the JSON object.",
    )

    raw = _parse_json_object(text, context=f"brief user={user_id}")
    return _validate_brief(raw, user_id)


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
                selected_chips=["AI", "Python", "open source software"],
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
