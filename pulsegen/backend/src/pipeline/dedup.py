"""
Stage 2 (programmatic): Deduplication — checks PostgreSQL for an existing url_hash
before any LLM call is made.

Fail-open policy: if the DB call errors, we return False (allow through) so we
never silently drop a document due to an infra hiccup.
"""

from __future__ import annotations

import hashlib
import logging

from src.config import settings

logger = logging.getLogger(__name__)


def compute_url_hash(url: str) -> str:
    """SHA-256 hex digest of the raw URL string."""
    return hashlib.sha256(url.encode()).hexdigest()


def is_duplicate(url: str) -> bool:
    """
    Query PostgreSQL to check whether a document with the given URL has already
    been stored in generator_documents.

    Returns:
        True  — document already exists; pipeline should skip it.
        False — document is new (or DB errored; fail-open).
    """
    url_hash = compute_url_hash(url)
    db_url = settings.storage_database_url
    if not db_url:
        logger.warning("STORAGE_DATABASE_URL not set — dedup disabled, allowing through.")
        return False
    try:
        import psycopg2

        conn = psycopg2.connect(db_url, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM generator_documents WHERE url_hash = %s LIMIT 1",
                (url_hash,),
            )
            exists = cur.fetchone() is not None
        conn.close()
        if exists:
            logger.debug("Dedup: url_hash=%s already in DB, skipping.", url_hash)
        return exists
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Dedup error for url_hash=%s: %s — failing open (allowing through).",
            url_hash,
            exc,
        )
        return False
