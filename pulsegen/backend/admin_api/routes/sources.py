"""
GET /admin/sources — per-connector quality records (pass rates, last harvest).
Reads from SQLite source_quality table (via GENERATOR_DB_PATH).
"""

import logging
import sqlite3

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class SourceRecord(BaseModel):
    source_id: str
    total_fetched: int
    total_passed_gate: int
    total_stored: int
    pass_rate: float
    last_updated: str | None


def _get_db_connection() -> sqlite3.Connection | None:
    import os

    db_path = os.environ.get("GENERATOR_DB_PATH", "generator.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as exc:
        logger.warning("Could not open generator.db: %s", exc)
        return None


@router.get("/sources")
def get_sources() -> list[SourceRecord]:
    """Return per-source quality records."""
    conn = _get_db_connection()
    if conn is None:
        return []

    try:
        rows = conn.execute(
            "SELECT source_id, total_fetched, total_passed_gate, total_stored, last_updated "
            "FROM source_quality ORDER BY total_fetched DESC"
        ).fetchall()

        records = []
        for row in rows:
            source_id = row["source_id"]
            fetched = row["total_fetched"]
            passed = row["total_passed_gate"]
            stored = row["total_stored"]
            last_updated = row["last_updated"]

            # Pass rate: passed / fetched, default 0.5 if no data
            pass_rate = (passed / fetched) if fetched > 0 else 0.5

            records.append(
                SourceRecord(
                    source_id=source_id,
                    total_fetched=fetched,
                    total_passed_gate=passed,
                    total_stored=stored,
                    pass_rate=pass_rate,
                    last_updated=last_updated,
                )
            )
        return records
    except Exception as exc:
        logger.error("Failed to fetch sources: %s", exc)
        return []
    finally:
        conn.close()
