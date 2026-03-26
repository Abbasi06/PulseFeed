from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS trend_keywords (
        id           INTEGER PRIMARY KEY,
        run_id       TEXT    NOT NULL,
        term         TEXT    NOT NULL,
        category     TEXT    NOT NULL,
        context      TEXT    NOT NULL DEFAULT '',
        source_count INTEGER NOT NULL DEFAULT 0,
        collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_trend_keywords_collected_at ON trend_keywords(collected_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_trend_keywords_run_id ON trend_keywords(run_id)",
    """
    CREATE TABLE IF NOT EXISTS generator_documents (
        id                    INTEGER PRIMARY KEY,
        source                TEXT NOT NULL,
        source_id             TEXT NOT NULL,
        url                   TEXT NOT NULL,
        url_hash              TEXT NOT NULL UNIQUE,
        content_hash          TEXT NOT NULL,
        title                 TEXT NOT NULL DEFAULT '',
        author                TEXT NOT NULL DEFAULT '',
        published_at          TEXT NOT NULL DEFAULT '',
        summary               TEXT NOT NULL DEFAULT '',
        bm25_keywords         TEXT NOT NULL DEFAULT '[]',
        taxonomy_tags         TEXT NOT NULL DEFAULT '[]',
        image_url             TEXT NOT NULL DEFAULT '',
        gatekeeper_confidence REAL NOT NULL DEFAULT 0.0,
        embedding_id          TEXT,
        fts_rowid             INTEGER,
        processed_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        pipeline_status       TEXT NOT NULL DEFAULT 'complete'
    )
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS generator_fts USING fts5(
        title,
        keywords,
        entities,
        content=generator_documents,
        content_rowid=id
    )
    """,
]


def db_path() -> str:
    """Return the generator DB path from env or a sensible default next to this package."""
    env_val = os.environ.get("GENERATOR_DB_PATH")
    if env_val:
        return env_val
    # Default: generator.db in the backend/ directory (sibling of this package)
    return str(Path(__file__).parent.parent / "generator.db")


def init_db() -> None:
    """Create generator tables if they don't exist. Safe to call multiple times."""
    path = db_path()
    logger.info("Initialising generator DB at %s", path)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        for ddl in _DDL:
            conn.execute(ddl)
        conn.commit()
        logger.info("Generator DB ready")
    finally:
        conn.close()
