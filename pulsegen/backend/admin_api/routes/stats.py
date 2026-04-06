"""
GET /admin/stats — pipeline document counts and recent documents.
Reads from PostgreSQL generator_documents table.
"""

import json
import logging
from typing import Any

import psycopg2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class StatsResponse(BaseModel):
    total_documents: int
    by_source: dict[str, int]
    by_taxonomy: list[dict[str, Any]]
    by_status: dict[str, int]
    recent_documents: list[dict[str, Any]]
    db_available: bool


def _get_connection() -> psycopg2.extensions.connection | None:
    import os

    db_url = os.environ.get("STORAGE_DATABASE_URL")
    if not db_url:
        return None
    try:
        return psycopg2.connect(db_url)
    except Exception as exc:
        logger.warning("Could not connect to PostgreSQL: %s", exc)
        return None


@router.get("/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    """Return pipeline statistics from PostgreSQL."""
    conn = _get_connection()
    if conn is None:
        return StatsResponse(
            total_documents=0,
            by_source={},
            by_taxonomy=[],
            by_status={},
            recent_documents=[],
            db_available=False,
        )

    try:
        cur = conn.cursor()

        # Total documents
        cur.execute("SELECT COUNT(*) FROM generator_documents")
        total = cur.fetchone()[0]

        # By source
        cur.execute(
            "SELECT source, COUNT(*) as n FROM generator_documents GROUP BY source"
        )
        by_source = {row[0]: row[1] for row in cur.fetchall()}

        # By taxonomy (tag frequency)
        cur.execute(
            "SELECT taxonomy_tags FROM generator_documents WHERE taxonomy_tags IS NOT NULL"
        )
        tag_counts: dict[str, int] = {}
        for (tags_json,) in cur.fetchall():
            try:
                tags = json.loads(tags_json or "[]")
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except Exception:
                pass
        by_taxonomy: list[dict[str, Any]] = sorted(
            [{"tag": t, "count": c} for t, c in tag_counts.items()],
            key=lambda x: int(x.get("count") or 0),
            reverse=True,
        )

        # By status (pipeline_status)
        cur.execute(
            "SELECT pipeline_status, COUNT(*) as n FROM generator_documents GROUP BY pipeline_status"
        )
        by_status = {row[0]: row[1] for row in cur.fetchall()}

        # Recent 10 documents
        cur.execute(
            """SELECT id, title, source, taxonomy_tags, gatekeeper_confidence, processed_at, url
               FROM generator_documents ORDER BY processed_at DESC LIMIT 10"""
        )
        recent_documents = []
        for row in cur.fetchall():
            doc_id, title, source, tags_json, confidence, processed_at, url = row
            try:
                tags = json.loads(tags_json or "[]")
            except Exception:
                tags = []
            recent_documents.append(
                {
                    "id": str(doc_id),
                    "title": title,
                    "source": source,
                    "tags": tags,
                    "confidence": round(confidence, 2) if confidence else 0.0,
                    "processed_at": processed_at.isoformat() if processed_at else None,
                    "url": url,
                }
            )

        cur.close()
        return StatsResponse(
            total_documents=total,
            by_source=by_source,
            by_taxonomy=by_taxonomy,
            by_status=by_status,
            recent_documents=recent_documents,
            db_available=True,
        )
    except Exception as exc:
        logger.error("Failed to fetch stats: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()
