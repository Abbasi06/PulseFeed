"""
GET /admin/trends/keywords — recent batch of extracted trend keywords
GET /admin/trends/runs     — run metadata
"""

import logging
import sqlite3

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class TrendKeyword(BaseModel):
    term: str
    category: str
    context: str
    source_count: int


class TrendRun(BaseModel):
    run_id: str
    collected_at: str
    docs_analyzed: int


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


@router.get("/trends/keywords")
def get_trend_keywords(limit: int = 100) -> list[TrendKeyword]:
    """Return recent trend keywords."""
    limit = min(limit, 500)  # cap at 500
    conn = _get_db_connection()
    if conn is None:
        return []

    try:
        rows = conn.execute(
            """SELECT term, category, context, source_count
               FROM trend_keywords
               ORDER BY collected_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

        return [
            TrendKeyword(
                term=row["term"],
                category=row["category"],
                context=row["context"],
                source_count=row["source_count"],
            )
            for row in rows
        ]
    except Exception as exc:
        logger.error("Failed to fetch trend keywords: %s", exc)
        return []
    finally:
        conn.close()


@router.get("/trends/runs")
def get_trend_runs(limit: int = 20) -> list[TrendRun]:
    """Return recent trend analysis run metadata."""
    limit = min(limit, 100)
    conn = _get_db_connection()
    if conn is None:
        return []

    try:
        rows = conn.execute(
            """SELECT DISTINCT run_id, collected_at, source_count
               FROM trend_keywords
               ORDER BY collected_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

        return [
            TrendRun(
                run_id=row["run_id"],
                collected_at=row["collected_at"],
                docs_analyzed=row["source_count"],
            )
            for row in rows
        ]
    except Exception as exc:
        logger.error("Failed to fetch trend runs: %s", exc)
        return []
    finally:
        conn.close()
