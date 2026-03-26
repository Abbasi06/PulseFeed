"""
Feed Personalizer
-----------------
Builds a user's personalized feed by querying the application-wide
generator.db (written by PulseGen) using FTS5 full-text search.

No Gemini call is made in the happy path — matching is keyword/BM25 based,
making this very cheap and fast enough to run every 5 minutes.

Falls back to research_agent.generate_feed() if generator.db is unavailable
or returns fewer than MIN_FTS_RESULTS matching documents.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from models import User

logger = logging.getLogger(__name__)

MIN_FTS_RESULTS = 5  # fall back to research_agent below this
TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# DB helpers (read-only)
# ---------------------------------------------------------------------------


def _open_generator_db() -> sqlite3.Connection | None:
    """Open generator.db in read-only mode. Returns None if the file does not exist."""
    from generator.db import db_path

    path = db_path()
    import os

    if not os.path.exists(path):
        logger.warning("generator.db not found at %s — will fall back to research_agent", path)
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as exc:
        logger.warning("Could not open generator.db: %s", exc)
        return None


def _sanitize_term(term: str) -> str:
    """Remove FTS5 special characters so terms can be wrapped in double-quotes."""
    return re.sub(r'["\(\)\*\+\-]', " ", term).strip()


def _build_fts_query(user: User) -> str:
    """
    Build an FTS5 MATCH query from the user's interests.

    Each interest is wrapped in double-quotes for exact phrase matching.
    Terms are joined with OR so a document matching any interest scores.
    """
    sub_fields: list[str] = getattr(user, "sub_fields", None) or []
    chips: list[str] = getattr(user, "selected_chips", None) or []
    occupation: str = getattr(user, "occupation", "") or ""

    # Prefer detailed sub_fields; fall back to selected_chips
    terms = sub_fields if sub_fields else chips

    # Always include occupation as a signal
    if occupation:
        terms = [occupation] + [t for t in terms if t.lower() != occupation.lower()]

    # Take at most 7 terms, sanitize, wrap in quotes
    quoted: list[str] = []
    for t in terms[:7]:
        clean = _sanitize_term(t)
        if clean:
            quoted.append(f'"{clean}"')

    return " OR ".join(quoted) if quoted else '""'


def _fts_search(
    conn: sqlite3.Connection,
    fts_query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Search generator_fts using FTS5 BM25 ranking.

    bm25() returns negative values — lower (more negative) = better match.
    ORDER BY rank ASC gives best matches first.
    """
    try:
        rows = conn.execute(
            """
            SELECT d.id, d.title, d.summary, d.source, d.url,
                   d.published_at, d.taxonomy_tags, d.image_url,
                   d.gatekeeper_confidence,
                   bm25(generator_fts) AS rank
            FROM generator_fts
            JOIN generator_documents d ON generator_fts.rowid = d.id
            WHERE generator_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("FTS search failed (%r): %s", fts_query, exc)
        return []


def _fallback_recent(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    """Return the most-recent high-confidence docs when FTS finds nothing."""
    try:
        rows = conn.execute(
            """
            SELECT id, title, summary, source, url, published_at,
                   taxonomy_tags, image_url, gatekeeper_confidence
            FROM generator_documents
            ORDER BY processed_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("Fallback recent query failed: %s", exc)
        return []


def _rows_to_feed_items(rows: list[dict[str, Any]], user_id: int) -> list[dict[str, Any]]:
    """Convert generator_documents rows to the shape _save_items() expects."""
    out: list[dict[str, Any]] = []
    for r in rows:
        # taxonomy_tags is stored as JSON array; use first tag as 'topic'
        tags: list[str] = []
        try:
            tags = json.loads(r.get("taxonomy_tags") or "[]")
        except Exception:
            pass
        topic = tags[0] if tags else "General"

        title = (r.get("title") or "").strip()
        summary = (r.get("summary") or "").strip()
        if not title and not summary:
            continue

        out.append(
            {
                "user_id": user_id,
                "title": title or "Untitled",
                "summary": summary,
                "source": r.get("source") or "Unknown",
                "url": r.get("url") or "#",
                "topic": topic,
                "image_url": r.get("image_url") or "",
                "published_date": r.get("published_at") or TODAY,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Sync version — used by the APScheduler batch job (no event loop)
# ---------------------------------------------------------------------------


def personalize_feed_sync(user_id: int) -> list[dict[str, Any]]:
    """
    Synchronous personalisation from generator.db only (no Gemini, no fallback).
    Returns an empty list if generator.db is unavailable or empty.
    Called from the 5-minute APScheduler batch refresh job in main.py.
    """
    from database import engine
    from sqlalchemy.orm import Session as SASession

    db = SASession(engine)
    try:
        user = db.get(User, user_id)
        if user is None:
            return []

        conn = _open_generator_db()
        if conn is None:
            return []

        try:
            fts_query = _build_fts_query(user)
            rows = _fts_search(conn, fts_query, limit=20)
            if len(rows) < MIN_FTS_RESULTS:
                # Not enough relevant content in generator.db — skip so the
                # async route can fall back to research_agent on next request.
                return []
            return _rows_to_feed_items(rows, user_id)
        finally:
            conn.close()
    except Exception as exc:
        logger.error("personalize_feed_sync failed for user %d: %s", user_id, exc)
        return []
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Async version — used by feed.py route handlers
# ---------------------------------------------------------------------------


async def personalize_feed(user_id: int, db: Session) -> list[dict[str, Any]]:
    """
    Async personalisation entry point.  Queries generator.db for matching
    content.  Falls back to research_agent.generate_feed() if the pool is
    too small.
    """
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    conn = _open_generator_db()
    if conn is None:
        logger.info("generator.db unavailable — falling back to research_agent for user %d", user_id)
        from agents.research_agent import generate_feed
        return await generate_feed(user_id, db)

    try:
        fts_query = _build_fts_query(user)
        rows = _fts_search(conn, fts_query, limit=20)

        if len(rows) < MIN_FTS_RESULTS:
            logger.info(
                "Only %d FTS results for user %d — falling back to research_agent",
                len(rows),
                user_id,
            )
            conn.close()
            from agents.research_agent import generate_feed
            return await generate_feed(user_id, db)

        items = _rows_to_feed_items(rows, user_id)
        logger.info("personalize_feed user=%d: %d items from generator pool", user_id, len(items))
        return items
    finally:
        conn.close()
