"""
Feed Personalizer
-----------------
Builds a user's personalized feed by querying PostgreSQL generator_documents table
using full-text search (FTS).

No Gemini call is made in the happy path — matching is keyword/BM25 based,
making this very cheap and fast enough to run every 5 minutes.

Returns empty feed if PostgreSQL is unavailable or no matching documents found.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

import psycopg2
from sqlalchemy.orm import Session

from models import User

logger = logging.getLogger(__name__)

MIN_FTS_RESULTS = 5
TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# DB helpers (read-only PostgreSQL)
# ---------------------------------------------------------------------------


def _open_generator_pg() -> psycopg2.extensions.connection | None:
    """Open PostgreSQL connection to shared database. Returns None if unavailable."""
    import os

    url = os.environ.get("STORAGE_DATABASE_URL")
    if not url:
        logger.warning("STORAGE_DATABASE_URL not set — generator pool unavailable")
        return None
    try:
        conn = psycopg2.connect(url)
        return conn
    except Exception as exc:
        logger.warning("Could not connect to generator PostgreSQL: %s", exc)
        return None


def _sanitize_term(term: str) -> str:
    """Remove special characters so terms can be safely used in FTS queries."""
    return re.sub(r'["\(\)\*\+\-&|!<>]', " ", term).strip()


def _build_fts_query(user: User) -> str:
    """
    Build a PostgreSQL FTS query from the user's interests.

    Each interest is wrapped in single-quotes for phrase matching.
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

    # Take at most 7 terms, sanitize
    query_parts: list[str] = []
    for t in terms[:7]:
        clean = _sanitize_term(t)
        if clean:
            query_parts.append(clean)

    return " | ".join(query_parts) if query_parts else ""


def _fts_search(
    conn: psycopg2.extensions.connection,
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Search generator_documents using PostgreSQL FTS.

    Uses to_tsvector and plainto_tsquery for robust full-text search.
    """
    if not query:
        return []

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, summary, source, url,
                   published_at, taxonomy_tags, image_url,
                   gatekeeper_confidence
            FROM generator_documents
            WHERE to_tsvector('english', COALESCE(summary, '') || ' ' ||
                              COALESCE(array_to_string(bm25_keywords, ' '), ''))
                  @@ plainto_tsquery('english', %s)
            ORDER BY processed_at DESC
            LIMIT %s
            """,
            (query, limit),
        )
        rows = cur.fetchall()
        cur.close()

        result: list[dict[str, Any]] = []
        for row in rows:
            result.append({
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "source": row[3],
                "url": row[4],
                "published_at": row[5],
                "taxonomy_tags": row[6],
                "image_url": row[7],
                "gatekeeper_confidence": row[8],
            })
        return result
    except Exception as exc:
        logger.warning("FTS search failed (%r): %s", query, exc)
        return []


def _rows_to_feed_items(rows: list[dict[str, Any]], user_id: int) -> list[dict[str, Any]]:
    """Convert generator_documents rows to the shape feed routes expect."""
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

        out.append({
            "user_id": user_id,
            "title": title or "Untitled",
            "summary": summary,
            "source": r.get("source") or "Unknown",
            "url": r.get("url") or "#",
            "topic": topic,
            "image_url": r.get("image_url") or "",
            "published_date": r.get("published_at") or TODAY,
        })
    return out


# ---------------------------------------------------------------------------
# Sync version — used by the APScheduler batch job
# ---------------------------------------------------------------------------


def personalize_feed_sync(user_id: int) -> list[dict[str, Any]]:
    """
    Synchronous personalisation from PostgreSQL only.
    Returns an empty list if PostgreSQL is unavailable or no matches found.
    Called from the 5-minute APScheduler batch refresh job in main.py.
    """
    from database import engine
    from sqlalchemy.orm import Session as SASession

    db = SASession(engine)
    try:
        user = db.get(User, user_id)
        if user is None:
            return []

        conn = _open_generator_pg()
        if conn is None:
            return []

        try:
            fts_query = _build_fts_query(user)
            rows = _fts_search(conn, fts_query, limit=20)
            if len(rows) < MIN_FTS_RESULTS:
                logger.info(
                    "Only %d FTS results for user %d — generator pool insufficient",
                    len(rows),
                    user_id,
                )
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
    Async personalisation entry point. Queries PostgreSQL for matching content.
    Returns empty list if the pool is unavailable or insufficient.
    """
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    conn = _open_generator_pg()
    if conn is None:
        logger.info("Generator pool unavailable — returning empty feed for user %d", user_id)
        return []

    try:
        fts_query = _build_fts_query(user)
        rows = _fts_search(conn, fts_query, limit=20)

        if len(rows) < MIN_FTS_RESULTS:
            logger.info(
                "Only %d FTS results for user %d — generator pool insufficient",
                len(rows),
                user_id,
            )
            return []

        items = _rows_to_feed_items(rows, user_id)
        logger.info("personalize_feed user=%d: %d items from generator pool", user_id, len(items))
        return items
    finally:
        conn.close()
