"""
Trend Scheduler Job
--------------------
Every 30 minutes, reads the N most-recent summaries from generator.db,
runs TrendAnalystAgent, and persists the extracted keywords to the
trend_keywords table.
"""
from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .db import db_path
from .status_store import AGENT_STATUS
from .trend_analyst import TrendAnalystAgent

logger = logging.getLogger(__name__)

_DOCS_TO_ANALYZE = 30  # number of recent summaries fed to the analyst


def run_trend_job(scheduler: Any = None) -> None:
    """Run one trend analysis cycle. Scheduled every 30 minutes."""
    status = AGENT_STATUS["trend_analyst"]
    now = datetime.now(tz=timezone.utc).isoformat()
    status.update({
        "state": "running",
        "started_at": now,
        "docs_analyzed": 0,
        "trends_found": 0,
        "error_message": None,
    })

    try:
        conn = sqlite3.connect(db_path())
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")

        # Read recent summaries
        rows = conn.execute(
            """
            SELECT summary, title FROM generator_documents
            WHERE summary != ''
            ORDER BY processed_at DESC
            LIMIT ?
            """,
            (_DOCS_TO_ANALYZE,),
        ).fetchall()

        if not rows:
            logger.info("Trend job: no documents yet — skipping")
            status.update({
                "state": "idle",
                "finished_at": datetime.now(tz=timezone.utc).isoformat(),
            })
            conn.close()
            return

        # Concatenate all summaries into one corpus
        corpus = "\n\n".join(
            f"Title: {r['title']}\n{r['summary']}" for r in rows
        )
        doc_count = len(rows)
        status["docs_analyzed"] = doc_count
        logger.info("Trend job: analyzing %d documents", doc_count)

        # Run Trend Analyst
        agent = TrendAnalystAgent()
        result = agent.analyze(corpus)

        if not result.extracted_trends:
            logger.info("Trend job: no trends extracted")
            finish = datetime.now(tz=timezone.utc).isoformat()
            status.update({
                "state": "success",
                "finished_at": finish,
                "last_run_at": finish,
                "trends_found": 0,
            })
            conn.close()
            return

        run_id = str(uuid.uuid4())
        collected_at = datetime.now(tz=timezone.utc).isoformat()

        for trend in result.extracted_trends:
            conn.execute(
                """
                INSERT INTO trend_keywords
                    (run_id, term, category, context, source_count, collected_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    trend.term,
                    trend.category.value,
                    trend.context,
                    doc_count,
                    collected_at,
                ),
            )
        conn.commit()
        conn.close()

        finish = datetime.now(tz=timezone.utc).isoformat()
        status.update({
            "state": "success",
            "finished_at": finish,
            "last_run_at": finish,
            "trends_found": len(result.extracted_trends),
            "last_run_id": run_id,
            "error_message": None,
        })
        logger.info(
            "Trend job done — docs_analyzed=%d trends_found=%d run_id=%s",
            doc_count,
            len(result.extracted_trends),
            run_id,
        )

    except Exception as exc:
        logger.error("Trend job failed: %s", exc, exc_info=True)
        status.update({
            "state": "error",
            "finished_at": datetime.now(tz=timezone.utc).isoformat(),
            "error_message": str(exc)[:300],
        })

    finally:
        if scheduler:
            job = scheduler.get_job("trend_analyst")
            if job and getattr(job, "next_run_time", None):
                status["next_run_at"] = job.next_run_time.isoformat()
