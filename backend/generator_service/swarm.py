"""
Generator Swarm
---------------
Runs 6 topic-focused harvest workers in parallel using a ThreadPoolExecutor.
Each worker covers a distinct domain and feeds into the shared generator.db.

All Gemini quota (429) retries happen inside the individual pipeline helpers
(_gemini_call, _run_gatekeeper_batch, _run_extractor) which already have
retry logic — no extra handling needed here.
"""
from __future__ import annotations

import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from generator.db import db_path
from generator.inline_pipeline import (
    _MIN_WORDS,
    _content_hash,
    _fetch_arxiv,
    _fetch_ddg,
    _gemini_client,
    _is_duplicate,
    _run_extractor,
    _run_gatekeeper_batch,
    _store_document,
)
from generator.status_store import AGENT_STATUS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Topic worker definitions
# Each entry: name, arxiv_queries, ddg_queries
# Queries are domain-scoped rewrites of the existing _ARXIV/DDG_QUERY_POOLs
# ---------------------------------------------------------------------------

TOPICS: list[dict[str, Any]] = [
    {
        "name": "AI/ML Systems",
        "arxiv_queries": [
            "large language model inference serving latency optimization",
            "autonomous LLM agent framework tool use multi-step reasoning",
            "retrieval augmented generation RAG system design architecture",
            "reinforcement learning human feedback RLHF alignment fine-tuning",
            "mixture of experts MoE sparse model scaling efficiency",
        ],
        "ddg_queries": [
            "LLM production deployment optimization cost latency 2026",
            "AI agent autonomous framework engineering news 2026",
            "open source AI model serving performance benchmark",
        ],
    },
    {
        "name": "Cloud & DevOps",
        "arxiv_queries": [
            "Kubernetes GPU scheduling ML workload orchestration",
            "distributed systems consensus fault tolerance scalability",
        ],
        "ddg_queries": [
            "cloud infrastructure DevOps SRE platform engineering 2026",
            "Kubernetes container orchestration resource optimization 2026",
            "MLOps GPU cluster distributed training platform news",
        ],
    },
    {
        "name": "Data Engineering",
        "arxiv_queries": [
            "MLOps observability vector database production deployment",
            "efficient attention sparse transformer long context streaming",
        ],
        "ddg_queries": [
            "data engineering pipeline real-time streaming processing 2026",
            "vector database semantic search infrastructure benchmark",
            "database performance distributed SQL NoSQL engineering 2026",
        ],
    },
    {
        "name": "Security & Privacy",
        "arxiv_queries": [
            "federated learning privacy distributed training optimization",
            "model quantization pruning compression inference edge privacy",
        ],
        "ddg_queries": [
            "cybersecurity zero-trust architecture engineering 2026",
            "privacy preserving machine learning differential privacy 2026",
        ],
    },
    {
        "name": "Developer Tools & Open Source",
        "arxiv_queries": [
            "software engineering productivity automated testing code generation",
        ],
        "ddg_queries": [
            "developer tools AI assistant coding engineering productivity 2026",
            "open source framework library release engineering 2026",
            "developer experience platform internal tooling 2026",
        ],
    },
    {
        "name": "Systems & Performance",
        "arxiv_queries": [
            "transformer hardware acceleration GPU memory efficiency chip",
            "diffusion model generation architecture systems engineering",
            "eBPF kernel observability systems programming performance",
        ],
        "ddg_queries": [
            "AI hardware accelerator chip inference systems design 2026",
            "eBPF observability tracing Linux kernel systems 2026",
        ],
    },
]

_ARXIV_PER_QUERY = 5
_DDG_PER_QUERY = 6


# ---------------------------------------------------------------------------
# Per-topic worker (runs in a thread)
# ---------------------------------------------------------------------------


def _worker(
    topic: dict[str, Any],
    client: Any,
    target_docs: int,
) -> dict[str, Any]:
    """
    One topic worker: harvest → dedup → gate → extract → store.
    Opens its own sqlite3 connection (not thread-safe to share one).
    Returns a summary dict with counter totals.
    """
    name = topic["name"]
    counts: dict[str, int] = {
        "harvested": 0,
        "passed_gate": 0,
        "extracted": 0,
        "stored": 0,
        "skipped": 0,
    }

    try:
        conn = sqlite3.connect(db_path())
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")

        seen: set[str] = set()
        raw: list[dict[str, Any]] = []

        for q in topic.get("arxiv_queries", []):
            raw.extend(_fetch_arxiv(q, _ARXIV_PER_QUERY))
        for q in topic.get("ddg_queries", []):
            raw.extend(_fetch_ddg(q, _DDG_PER_QUERY))

        # Dedup + word count filter
        unique: list[dict[str, Any]] = []
        for item in raw:
            url = item.get("url", "")
            body = item.get("body", "")
            if not url or url in seen:
                counts["skipped"] += 1
                continue
            if len(body.split()) < _MIN_WORDS:
                counts["skipped"] += 1
                continue
            ch = _content_hash(url, body)
            if _is_duplicate(conn, url, ch):
                seen.add(url)
                counts["skipped"] += 1
                continue
            seen.add(url)
            item["_ch"] = ch
            unique.append(item)

        counts["harvested"] = len(unique)
        logger.info("[%s] harvested %d unique candidates", name, len(unique))

        if not unique:
            conn.close()
            return counts

        # Gatekeeper (one batch call for this topic)
        gate_results = _run_gatekeeper_batch(client, unique)
        passed = [
            (item, gate)
            for item, gate in zip(unique, gate_results)
            if gate is not None
        ]
        counts["passed_gate"] = len(passed)
        logger.info("[%s] gatekeeper passed %d/%d", name, len(passed), len(unique))

        # Extract + store
        for item, gate in passed:
            if counts["stored"] >= target_docs:
                break
            extracted = _run_extractor(client, item.get("body", ""))
            if extracted is None:
                counts["skipped"] += 1
                continue
            counts["extracted"] += 1

            stored = _store_document(
                conn,
                url=item["url"],
                source=item.get("source", "rss"),
                title=item.get("title", ""),
                author=item.get("author", "Unknown"),
                published_at=item.get("published_at", ""),
                content_hash=item["_ch"],
                extracted=extracted,
                gate_confidence=gate.confidence,
            )
            if stored:
                counts["stored"] += 1
                logger.info(
                    "[%s] stored (%d/%d): %s",
                    name,
                    counts["stored"],
                    target_docs,
                    item.get("title", "")[:60],
                )

        conn.close()

    except Exception as exc:
        logger.error("[%s] worker failed: %s", name, exc, exc_info=True)

    return counts


# ---------------------------------------------------------------------------
# Main swarm job — called by APScheduler
# ---------------------------------------------------------------------------


def run_swarm_job(
    scheduler: Any = None,
    target_docs_per_topic: int = 5,
) -> None:
    """
    Launch one worker per topic in parallel and aggregate results into
    AGENT_STATUS['generator'].  Called by APScheduler every N minutes.
    """
    status = AGENT_STATUS["generator"]
    now = datetime.now(tz=timezone.utc).isoformat()
    status.update(
        {
            "state": "running",
            "phase": 1,
            "phase_label": "Swarm Harvest",
            "started_at": now,
            "docs_harvested": 0,
            "docs_passed_gate": 0,
            "docs_extracted": 0,
            "docs_stored": 0,
            "docs_skipped": 0,
            "error_message": None,
        }
    )

    try:
        client = _gemini_client()
    except ValueError as exc:
        status.update(
            {
                "state": "error",
                "error_message": str(exc),
                "finished_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        logger.error("Swarm: %s", exc)
        return

    futures: dict[Any, str] = {}
    with ThreadPoolExecutor(max_workers=len(TOPICS), thread_name_prefix="swarm") as pool:
        for topic in TOPICS:
            fut = pool.submit(_worker, topic, client, target_docs_per_topic)
            futures[fut] = topic["name"]

        for fut in as_completed(futures):
            topic_name = futures[fut]
            try:
                counts = fut.result()
                status["docs_harvested"] += counts.get("harvested", 0)
                status["docs_passed_gate"] += counts.get("passed_gate", 0)
                status["docs_extracted"] += counts.get("extracted", 0)
                status["docs_stored"] += counts.get("stored", 0)
                status["docs_skipped"] += counts.get("skipped", 0)
                logger.info(
                    "Swarm topic %r done — stored=%d",
                    topic_name,
                    counts.get("stored", 0),
                )
            except Exception as exc:
                logger.error("Swarm topic %r raised: %s", topic_name, exc)

    finish = datetime.now(tz=timezone.utc).isoformat()
    status.update(
        {
            "state": "success",
            "phase": None,
            "phase_label": None,
            "finished_at": finish,
            "last_run_at": finish,
        }
    )
    logger.info(
        "Swarm done — harvested=%d passed_gate=%d stored=%d",
        status["docs_harvested"],
        status["docs_passed_gate"],
        status["docs_stored"],
    )

    if scheduler:
        job = scheduler.get_job("swarm")
        if job and getattr(job, "next_run_time", None):
            status["next_run_at"] = job.next_run_time.isoformat()
