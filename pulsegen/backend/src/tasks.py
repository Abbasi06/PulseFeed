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
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import redis as redis_lib
from celery import chord, group

from src.celery_app import app
from src.config import settings
from src.connectors import CONNECTOR_REGISTRY
from src.pipeline.bouncer import run_bouncer
from src.pipeline.dedup import is_duplicate
from src.pipeline.extractor import run_extractor
from src.pipeline.gatekeeper import run_gatekeeper
from src.schemas import (
    ExtractedDocument,
    RawDocument,
    StoragePayload,
)
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
        # After all source fetches complete, run cross-source amplification.
        chord(group(source_tasks))(post_cycle_amplify_task.si())

    logger.info(
        "harvest_cycle dispatched: %d sources, hot_topics=%s",
        len(cycle_plan),
        [q.hot_topics for q in [v[1] for v in cycle_plan.values()] if q.hot_topics],
    )
    return {"sources_dispatched": len(cycle_plan), "cycle_ts": datetime.now(UTC).isoformat()}


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


@app.task(name="src.tasks.post_cycle_amplify_task", bind=True)
def post_cycle_amplify_task(self: Any, _results: Any = None) -> dict[str, Any]:
    """
    Cross-source amplification — runs after all harvest_source_tasks complete.

    Reads documents stored in the last 10 minutes from PostgreSQL, detects
    entity terms that appeared in 2+ sources, and persists them to the
    amplified_signals SQLite table for the next cycle's query engine.

    Accepts _results from chord callback signature (ignored).
    """
    import psycopg2

    db_url = settings.storage_database_url
    try:
        conn = psycopg2.connect(db_url, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT title, source, source_id
                FROM generator_documents
                WHERE processed_at > NOW() - INTERVAL '10 minutes'
                ORDER BY processed_at DESC
                LIMIT 200
                """,
            )
            rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        logger.warning("post_cycle_amplify: could not read recent docs: %s", exc)
        return {"amplified": 0, "error": str(exc)}

    if not rows:
        logger.debug("post_cycle_amplify: no recent docs — skipping")
        return {"amplified": 0}

    # Build lightweight RawDocument-like objects (title + source for entity extraction)
    from src.schemas import DataSource

    docs: list[RawDocument] = []
    for title, source_str, source_id in rows:
        try:
            ds = DataSource(source_str)
        except ValueError:
            continue
        docs.append(
            RawDocument(
                source=ds,
                source_id=source_id or source_str,
                url=f"https://placeholder/{source_id}",
                title=title or "",
                body="",  # not needed for entity extraction
            )
        )

    signals = _get_coordinator().post_cycle_amplify(docs)
    logger.info("post_cycle_amplify: %d signals from %d docs", len(signals), len(docs))
    return {"amplified": len(signals), "docs_analyzed": len(docs)}


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
        if is_duplicate(doc.url):
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
    max_retries=6,
    default_retry_delay=90,
)
def gatekeeper_task(self: Any, raw_doc_dict: dict[str, Any]) -> None:
    """
    LLM Step 1: is_high_signal check.
    Skips if confidence below threshold. Chains to extractor on pass.
    """
    from openai import AsyncOpenAI

    doc = RawDocument.model_validate(raw_doc_dict)

    async def _run() -> Any:
        # Create the client inside the event loop so its cleanup runs before loop close.
        client = AsyncOpenAI(
            base_url=settings.llm_light_url, api_key=settings.llm_api_key
        )
        try:
            return await run_gatekeeper(
                client=client,
                model=settings.gatekeeper_model,
                doc_title=doc.title,
                doc_author=doc.author,
                doc_source=doc.source.value,
                doc_body_prefix=doc.body[:600],
            )
        finally:
            await client.close()

    try:
        gate = asyncio.run(_run())
    except Exception as exc:
        logger.warning("gatekeeper failed for '%s': %s", doc.title[:60], exc)
        raise self.retry(exc=exc, countdown=self.default_retry_delay)

    if gate.passes:
        logger.debug("GATE PASS [%.2f]: %s", gate.confidence, doc.title[:60])
        _get_coordinator().record_harvest_result(
            source_id=doc.source.value,
            fetched=0,
            passed_gate=1,
            stored=0,
        )
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
    max_retries=6,
    default_retry_delay=90,
    queue="extractor",  # dedicated queue — run with --concurrency=1
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
    doc = RawDocument.model_validate(raw_doc_dict)

    async def _run() -> Any:
        # Create the client inside the event loop so its cleanup runs before loop close.
        # 120s timeout: heavy model takes 50-80s; this prevents indefinite queue waits
        # that cause cancel storms on the llama.cpp server.
        from openai import AsyncOpenAI as _AsyncOpenAI
        from openai import Timeout as _Timeout

        client = _AsyncOpenAI(
            base_url=settings.llm_heavy_url,
            api_key=settings.llm_api_key,
            timeout=_Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
        )
        try:
            return await run_extractor(
                client=client,
                model=settings.extractor_model,
                body=doc.body,
            )
        finally:
            await client.close()

    try:
        extracted = asyncio.run(_run())
    except Exception as exc:
        logger.warning("extractor failed for '%s': %s", doc.title[:60], exc)
        raise self.retry(exc=exc, countdown=self.default_retry_delay)

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
        _get_coordinator().record_harvest_result(
            source_id=doc.source.value,
            fetched=0,
            passed_gate=0,
            stored=1,
        )
        logger.info(
            "STORED [%s] → %s | tags=%s",
            doc.title[:60],
            confirmation.document_id,
            extracted.taxonomy_tags,
        )
        return {"status": "stored", "document_id": confirmation.document_id}
    else:
        # route_to_postgres swallows exceptions — handle retries here.
        if self.request.retries >= self.max_retries:
            _dead_letter(payload, confirmation.error or "unknown storage failure")
            return {"status": "dead_lettered", "url": doc.url}
        raise self.retry(
            exc=RuntimeError(f"Storage failed: {confirmation.error}"),
        )


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _dead_letter(payload: StoragePayload, error: str) -> None:
    """Push failed payload to Redis dead-letter key for manual inspection."""
    entry = {
        "url": payload.url,
        "title": payload.title,
        "source": payload.source.value,
        "error": error,
        "failed_at": datetime.now(UTC).isoformat(),
    }
    try:
        r = redis_lib.from_url(settings.redis_url)
        r.lpush("pulsegen:dead_letter:storage", json.dumps(entry))
        r.ltrim("pulsegen:dead_letter:storage", 0, 499)  # cap at 500
        queue_size: int = r.llen("pulsegen:dead_letter:storage")  # type: ignore[assignment]
        if queue_size > 100:
            logger.critical(
                "Dead letter queue size=%d — storage failures may be systematic",
                queue_size,
            )
    except Exception as dl_exc:
        logger.critical(
            "Dead letter queue UNAVAILABLE (%s) — document LOST: url=%s title=%r",
            dl_exc,
            payload.url,
            payload.title[:60],
        )
    logger.error("DEAD LETTERED: %s — %s", payload.title[:60], error)


def _record_stored_tags(tags: Sequence[str]) -> None:
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
                (tag, datetime.now(UTC).isoformat()),
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
