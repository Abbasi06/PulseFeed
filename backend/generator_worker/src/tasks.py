"""
Celery task definitions for the PulseGen ingestion pipeline.

Task graph per harvest cycle:
  harvest_cycle()
    └─► harvest_source_task(source_id, queries, budget)  [one per source]
          └─► gatekeeper_task(raw_doc_dict)              [one per bounced doc]
                └─► extractor_task(raw_doc_dict, confidence)
                      └─► storage_router_task(raw_doc, extracted, confidence)

Cross-cutting:
  harvest_cycle() → post_cycle_amplify_task(all_doc_batch)
  trend_analysis_cycle()   → standalone, reads from SQLite
  prune_momentum_data()    → standalone cleanup
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from celery import chord, group
from src.celery_app import app
from src.config import settings
from src.connectors import CONNECTOR_REGISTRY
from src.pipeline.bouncer import run_bouncer
from src.pipeline.dedup import compute_url_hash, is_duplicate
from src.pipeline.gatekeeper import run_gatekeeper
from src.pipeline.extractor import run_extractor
from src.schemas import (
    DataSource,
    ExtractedDocument,
    RawDocument,
    StoragePayload,
    StorageConfirmation,
)
from src.storage.mcp_client import MCPClient
from src.storage.pg_router import route_to_postgres
from src.swarm.coordinator import SwarmCoordinator

logger = logging.getLogger(__name__)

# Module-level coordinator (one per worker process — lightweight)
_coordinator: SwarmCoordinator | None = None


def _get_coordinator() -> SwarmCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = SwarmCoordinator()
    return _coordinator


# ─── Cycle Orchestrators ──────────────────────────────────────────────────────


@app.task(name="src.tasks.harvest_cycle", bind=True, max_retries=1)
def harvest_cycle(self: Any) -> dict[str, Any]:
    """
    Beat-scheduled root task. Runs every 5 minutes.

    1. Ask SwarmCoordinator for the cycle plan (budgets + adaptive queries per source)
    2. Fan out one harvest_source_task per source
    3. After all sources complete, trigger cross-source amplification
    """
    coordinator = _get_coordinator()

    # Load tag counts from last cycle (stored in SQLite by storage_router_task)
    tag_counts = _load_last_cycle_tag_counts()
    cycle_plan = coordinator.plan_cycle(tag_counts)

    source_tasks = []
    for source_id, (budget, query_set) in cycle_plan.items():
        source_tasks.append(
            harvest_source_task.s(
                source_id,
                query_set.queries,
                budget,
            )
        )

    if source_tasks:
        # Fire-and-forget: results flow into gatekeeper tasks internally
        group(source_tasks).apply_async()

    logger.info(
        "harvest_cycle dispatched: %d sources, hot_topics=%s",
        len(cycle_plan),
        [q.hot_topics for q in [v[1] for v in cycle_plan.values()] if q.hot_topics],
    )
    return {"sources_dispatched": len(cycle_plan), "cycle_ts": datetime.utcnow().isoformat()}


@app.task(name="src.tasks.trend_analysis_cycle", bind=True, max_retries=1)
def trend_analysis_cycle(self: Any) -> dict[str, Any]:
    """
    Beat-scheduled trend extraction. Runs every 15 minutes.
    Reads 30 most-recent summaries from generator.db, runs TrendAnalystAgent,
    persists results to trend_keywords table.
    """
    try:
        # Import inline to avoid circular at module level
        from src.swarm.momentum import _run_trend_job

        result = _run_trend_job()
        logger.info("trend_analysis_cycle complete: %s", result)
        return result
    except Exception as exc:
        logger.error("trend_analysis_cycle failed: %s", exc)
        return {"error": str(exc)}


@app.task(name="src.tasks.prune_momentum_data", bind=True)
def prune_momentum_data(self: Any) -> dict[str, Any]:
    """Daily cleanup: remove momentum_cycles rows older than 30 days."""
    import sqlite3

    try:
        conn = sqlite3.connect(settings.generator_db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.execute(
            "DELETE FROM momentum_cycles WHERE cycle_ts < datetime('now', '-30 days')"
        )
        deleted = cur.rowcount
        conn.execute(
            "DELETE FROM amplified_signals WHERE recorded_at < datetime('now', '-7 days')"
        )
        conn.commit()
        conn.close()
        logger.info("prune_momentum_data: removed %d stale rows", deleted)
        return {"pruned_rows": deleted}
    except Exception as exc:
        logger.warning("prune_momentum_data failed (non-fatal): %s", exc)
        return {"error": str(exc)}


# ─── Per-Source Harvest ───────────────────────────────────────────────────────


@app.task(
    name="src.tasks.harvest_source_task",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def harvest_source_task(
    self: Any,
    source_id: str,
    queries: list[str],
    budget: int,
) -> dict[str, Any]:
    """
    Fetch documents from one source using its connector.
    Apply bouncer + dedup, then fan out to gatekeeper_task.

    The connector's fetch() method receives the query list so it can
    use adaptive queries rather than its internal fixed ones.
    """
    connector = CONNECTOR_REGISTRY.get(source_id)
    if connector is None:
        logger.error("harvest_source_task: unknown source_id '%s'", source_id)
        return {"source_id": source_id, "error": "unknown source"}

    try:
        # Pass extra queries to connectors that support it
        if hasattr(connector, "set_queries"):
            connector.set_queries(queries)

        docs: list[RawDocument] = asyncio.run(
            connector.fetch(max_results=budget)
        )
    except Exception as exc:
        logger.error("harvest[%s] fetch failed: %s", source_id, exc)
        raise self.retry(exc=exc)

    passed = 0
    skipped_bouncer = 0
    skipped_dedup = 0

    with MCPClient(settings.mcp_sql_command) as mcp:
        for doc in docs:
            # Stage 1: Heuristic bouncer
            bouncer_result = run_bouncer(doc)
            if not bouncer_result.passed:
                skipped_bouncer += 1
                logger.debug(
                    "BOUNCED [%s] %s: %s",
                    source_id,
                    bouncer_result.rejection_reason,
                    doc.title[:60],
                )
                continue

            # Stage 2: URL dedup against PostgreSQL
            if is_duplicate(doc.url, mcp):
                skipped_dedup += 1
                logger.debug("DEDUP [%s]: %s", source_id, doc.url[:80])
                continue

            # Fan out to gatekeeper
            gatekeeper_task.delay(doc.model_dump(mode="json"))
            passed += 1

    # Report back to coordinator for quality tracking
    _get_coordinator().record_harvest_result(
        source_id=source_id,
        fetched=len(docs),
        passed_gate=0,  # updated by gatekeeper_task
        stored=0,  # updated by storage_router_task
    )

    logger.info(
        "harvest[%s]: fetched=%d bounced=%d dedup=%d queued=%d",
        source_id,
        len(docs),
        skipped_bouncer,
        skipped_dedup,
        passed,
    )
    return {
        "source_id": source_id,
        "fetched": len(docs),
        "queued_for_gate": passed,
    }


# ─── Pipeline: Gatekeeper → Extractor → Storage ──────────────────────────────


@app.task(
    name="src.tasks.gatekeeper_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def gatekeeper_task(self: Any, raw_doc_dict: dict[str, Any]) -> None:
    """
    LLM Step 1: is_high_signal check.
    Skips if confidence below threshold. Chains to extractor on pass.
    """
    from google import genai

    doc = RawDocument.model_validate(raw_doc_dict)
    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        gate = asyncio.run(
            run_gatekeeper(
                client=client,
                model=settings.gatekeeper_model,
                doc_title=doc.title,
                doc_author=doc.author,
                doc_source=doc.source.value,
                doc_body_prefix=doc.body[:600],
            )
        )
    except Exception as exc:
        logger.warning("gatekeeper failed for '%s': %s", doc.title[:60], exc)
        raise self.retry(exc=exc)

    if gate.passes:
        logger.debug("GATE PASS [%.2f]: %s", gate.confidence, doc.title[:60])
        extractor_task.delay(raw_doc_dict, gate.confidence)
    else:
        logger.debug(
            "GATE REJECT [%.2f] %s: %s",
            gate.confidence,
            gate.reasoning or "",
            doc.title[:60],
        )


@app.task(
    name="src.tasks.extractor_task",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def extractor_task(
    self: Any,
    raw_doc_dict: dict[str, Any],
    gatekeeper_confidence: float,
) -> None:
    """
    LLM Step 2: deep extraction.
    Extracts summary, keywords, taxonomy tags, image URL.
    """
    from google import genai

    doc = RawDocument.model_validate(raw_doc_dict)
    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        extracted = asyncio.run(
            run_extractor(
                client=client,
                model=settings.extractor_model,
                body=doc.body,
            )
        )
    except Exception as exc:
        logger.warning("extractor failed for '%s': %s", doc.title[:60], exc)
        raise self.retry(exc=exc)

    logger.debug("EXTRACTED: %s | tags=%s", doc.title[:60], extracted.taxonomy_tags)
    storage_router_task.delay(
        raw_doc_dict,
        extracted.model_dump(mode="json"),
        gatekeeper_confidence,
    )


@app.task(
    name="src.tasks.storage_router_task",
    bind=True,
    max_retries=5,
    default_retry_delay=10,
)
def storage_router_task(
    self: Any,
    raw_doc_dict: dict[str, Any],
    extracted_dict: dict[str, Any],
    gatekeeper_confidence: float,
) -> dict[str, Any]:
    """
    Route final payload to PostgreSQL + pgvector via MCP.
    On final failure (all retries exhausted), dead-letters to Redis.
    """
    doc = RawDocument.model_validate(raw_doc_dict)
    extracted = ExtractedDocument.model_validate(extracted_dict)

    payload = StoragePayload(
        source=doc.source,
        source_id=doc.source_id,
        url=doc.url,
        url_hash=doc.url_hash,
        content_hash=doc.content_hash,
        title=doc.title,
        author=doc.author,
        published_at=doc.published_at,
        summary=extracted.summary,
        bm25_keywords=extracted.bm25_keywords,
        taxonomy_tags=extracted.taxonomy_tags,
        image_url=extracted.image_url,
        gatekeeper_confidence=gatekeeper_confidence,
    )

    try:
        confirmation = route_to_postgres(payload)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            _dead_letter(payload, str(exc))
            return {"status": "dead_lettered", "url": doc.url}
        raise self.retry(exc=exc)

    if confirmation.success:
        # Record taxonomy tag for momentum tracking
        _record_stored_tags(extracted.taxonomy_tags)
        logger.info(
            "STORED [%s] → %s | tags=%s",
            doc.title[:60],
            confirmation.document_id,
            extracted.taxonomy_tags,
        )
        return {"status": "stored", "document_id": confirmation.document_id}
    else:
        raise self.retry(
            exc=RuntimeError(f"Storage failed: {confirmation.error}"),
        )


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _dead_letter(payload: StoragePayload, error: str) -> None:
    """Push failed payload to Redis dead-letter key for manual inspection."""
    import redis as redis_lib

    r = redis_lib.from_url(settings.redis_url)
    entry = {
        "url": payload.url,
        "title": payload.title,
        "source": payload.source.value,
        "error": error,
        "failed_at": datetime.utcnow().isoformat(),
    }
    r.lpush("pulsegen:dead_letter:storage", json.dumps(entry))
    r.ltrim("pulsegen:dead_letter:storage", 0, 499)  # cap at 500
    logger.error("DEAD LETTERED: %s — %s", payload.title[:60], error)


def _record_stored_tags(tags: list[str]) -> None:
    """
    Increment per-tag counts in SQLite for momentum tracking.
    Uses a simple `current_cycle_tags` key in SQLite.
    """
    import sqlite3

    try:
        conn = sqlite3.connect(settings.generator_db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS current_cycle_tags (
                tag TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT
            )"""
        )
        for tag in tags:
            conn.execute(
                """INSERT INTO current_cycle_tags (tag, count, updated_at)
                   VALUES (?, 1, ?)
                   ON CONFLICT(tag) DO UPDATE SET
                     count = count + 1,
                     updated_at = excluded.updated_at""",
                (tag, datetime.utcnow().isoformat()),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("_record_stored_tags failed (non-fatal): %s", exc)


def _load_last_cycle_tag_counts() -> dict[str, int]:
    """
    Read current_cycle_tags, reset the table for the new cycle, return old counts.
    """
    import sqlite3

    try:
        conn = sqlite3.connect(settings.generator_db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS current_cycle_tags (
                tag TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT
            )"""
        )
        rows = conn.execute("SELECT tag, count FROM current_cycle_tags").fetchall()
        tag_counts = {row[0]: row[1] for row in rows}
        # Reset for new cycle
        conn.execute("DELETE FROM current_cycle_tags")
        conn.commit()
        conn.close()
        return tag_counts
    except Exception as exc:
        logger.warning("_load_last_cycle_tag_counts failed: %s", exc)
        return {}
