"""
Generator Observer Routes
--------------------------
Read-only API layer that reports on the isolated Generator pipeline and runs
the Trend Analyst on demand.  No writes to generator.db are made here — this
is purely an observer so the frontend can visualise what the pipeline has done.

Endpoints
---------
GET  /generator/stats          — pipeline stats read from generator.db
POST /generator/analyze        — run TrendAnalystAgent on arbitrary text
GET  /generator/agent-status   — live in-memory state of both background agents
GET  /generator/trend-keywords — most-recent batch of collected trend keywords
POST /generator/run-now        — manually trigger the ingestion pipeline
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generator", tags=["generator"])

_GENERATOR_DB = Path(__file__).parent.parent / "generator.db"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=15_000)


class AnalyzeResponse(BaseModel):
    extracted_trends: list[dict[str, str]]


class StatsResponse(BaseModel):
    total_documents: int
    by_source: dict[str, int]
    by_taxonomy: list[dict[str, Any]]
    by_status: dict[str, int]
    recent_documents: list[dict[str, Any]]
    db_available: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_db() -> sqlite3.Connection | None:
    if not _GENERATOR_DB.exists():
        return None
    conn = sqlite3.connect(str(_GENERATOR_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> Any:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# GET /generator/stats
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=StatsResponse)
def get_generator_stats() -> StatsResponse:
    """Return pipeline statistics read from generator.db."""
    conn = _open_db()
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
        total = _scalar(conn, "SELECT COUNT(*) FROM generator_documents")

        source_rows = conn.execute(
            "SELECT source, COUNT(*) AS n FROM generator_documents GROUP BY source"
        ).fetchall()
        by_source = {r["source"]: r["n"] for r in source_rows}

        taxonomy_rows = conn.execute(
            "SELECT taxonomy_tags FROM generator_documents WHERE taxonomy_tags != '[]'"
        ).fetchall()
        tag_counts: dict[str, int] = {}
        for row in taxonomy_rows:
            for tag in json.loads(row["taxonomy_tags"] or "[]"):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        by_taxonomy = sorted(
            [{"tag": t, "count": c} for t, c in tag_counts.items()],
            key=lambda x: x["count"],  # type: ignore[arg-type, return-value]
            reverse=True,
        )

        status_rows = conn.execute(
            "SELECT pipeline_status, COUNT(*) AS n FROM generator_documents GROUP BY pipeline_status"
        ).fetchall()
        by_status = {r["pipeline_status"]: r["n"] for r in status_rows}

        recent_rows = conn.execute(
            """SELECT id, title, source, taxonomy_tags, gatekeeper_confidence,
                      processed_at, url
               FROM generator_documents
               ORDER BY processed_at DESC LIMIT 10"""
        ).fetchall()
        recent_documents = [
            {
                "id":         r["id"],
                "title":      r["title"],
                "source":     r["source"],
                "tags":       json.loads(r["taxonomy_tags"] or "[]"),
                "confidence": round(r["gatekeeper_confidence"], 2),
                "processed_at": r["processed_at"],
                "url":        r["url"],
            }
            for r in recent_rows
        ]

        return StatsResponse(
            total_documents=total,
            by_source=by_source,
            by_taxonomy=by_taxonomy,
            by_status=by_status,
            recent_documents=recent_documents,
            db_available=True,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /generator/analyze
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_text(body: AnalyzeRequest) -> AnalyzeResponse:
    """Run the Trend Analyst Agent on submitted text and return extracted trends."""
    try:
        from generator.trend_analyst import TrendAnalystAgent
        agent = TrendAnalystAgent()
        result = agent.analyze(body.text)
        return AnalyzeResponse(
            extracted_trends=[t.model_dump() for t in result.extracted_trends]
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Trend analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail="Trend analysis failed") from exc


# ---------------------------------------------------------------------------
# GET /generator/agent-status
# ---------------------------------------------------------------------------


@router.get("/agent-status")
def get_agent_status() -> dict[str, Any]:
    """Return live in-memory state of both background agents."""
    from generator.status_store import AGENT_STATUS
    return dict(AGENT_STATUS)


# ---------------------------------------------------------------------------
# GET /generator/trend-keywords
# ---------------------------------------------------------------------------


class TrendKeywordsResponse(BaseModel):
    run_id: str | None = None
    collected_at: str | None = None
    docs_analyzed: int = 0
    keywords: list[dict[str, Any]] = Field(default_factory=list)
    db_available: bool = True


@router.get("/trend-keywords", response_model=TrendKeywordsResponse)
def get_trend_keywords(limit: int = 50) -> TrendKeywordsResponse:
    """Return the most recent batch of collected trend keywords."""
    limit = min(limit, 200)
    conn = _open_db()
    if conn is None:
        return TrendKeywordsResponse(db_available=False)
    try:
        # Find the latest run_id
        row = conn.execute(
            "SELECT run_id, collected_at, source_count FROM trend_keywords ORDER BY collected_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return TrendKeywordsResponse(db_available=True)

        run_id = row["run_id"]
        collected_at = row["collected_at"]
        source_count = row["source_count"]

        kw_rows = conn.execute(
            """
            SELECT term, category, context, source_count
            FROM trend_keywords
            WHERE run_id = ?
            ORDER BY category ASC, term ASC
            LIMIT ?
            """,
            (run_id, limit),
        ).fetchall()

        keywords = [
            {
                "term":         r["term"],
                "category":     r["category"],
                "context":      r["context"],
                "source_count": r["source_count"],
            }
            for r in kw_rows
        ]
        return TrendKeywordsResponse(
            run_id=run_id,
            collected_at=collected_at,
            docs_analyzed=source_count,
            keywords=keywords,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /generator/run-now
# ---------------------------------------------------------------------------


class RunNowResponse(BaseModel):
    accepted: bool
    message: str


@router.post("/run-now", response_model=RunNowResponse, status_code=202)
def run_now(
    background_tasks: BackgroundTasks,
    target_docs: int = Query(default=20, ge=1, le=200),
) -> RunNowResponse:
    """Manually trigger the swarm ingestion pipeline."""
    from generator.status_store import AGENT_STATUS
    from generator_service.swarm import TOPICS, run_swarm_job

    if AGENT_STATUS["generator"]["state"] == "running":
        raise HTTPException(status_code=409, detail="Pipeline is already running")

    per_topic = max(1, target_docs // len(TOPICS))
    background_tasks.add_task(run_swarm_job, target_docs_per_topic=per_topic)
    return RunNowResponse(
        accepted=True,
        message=f"Swarm queued — ~{per_topic} docs per topic ({len(TOPICS)} topics)",
    )


@router.post("/run-trend", response_model=RunNowResponse, status_code=202)
def run_trend(background_tasks: BackgroundTasks) -> RunNowResponse:
    """Manually trigger one trend analysis cycle as a background task."""
    from generator.status_store import AGENT_STATUS
    from generator.trend_scheduler import run_trend_job

    if AGENT_STATUS["trend_analyst"]["state"] == "running":
        raise HTTPException(status_code=409, detail="Trend analyst is already running")

    background_tasks.add_task(run_trend_job)
    return RunNowResponse(accepted=True, message="Trend analysis queued")
