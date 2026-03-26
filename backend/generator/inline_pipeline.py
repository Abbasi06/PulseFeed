"""
Inline Ingestion Pipeline
--------------------------
Runs the 4-phase Inference Cascade in-process, without MCP subprocesses.

Key design decisions
--------------------
* Phase 2 (Gatekeeper) is BATCHED — all candidates sent in ONE Gemini call
  instead of one call per document.  This reduces daily quota usage by ~10x.
* 429 RESOURCE_EXHAUSTED is handled: the retry delay is parsed from the error
  body and the call is retried automatically (up to max_retries times).
* run_ingestion_job() keeps looping through rotated query pools until
  `target_docs` are stored in generator.db or `max_rounds` is exhausted.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types as gtypes
from pydantic import ValidationError

from .db import db_path
from .prompts import build_extractor_prompt
from .schemas import ExtractedDocument, MetadataGatekeeperResult, TAXONOMY_TAGS
from .status_store import AGENT_STATUS

logger = logging.getLogger(__name__)

GATEKEEPER_MODEL = "gemini-2.5-flash-lite"  # 20 req/day — 1 batch call/round, max 5 rounds = 5 calls
EXTRACTOR_MODEL  = "gemini-2.5-flash"       # 25 req/day — 1 call/doc, separate daily quota
_JSON_CFG = gtypes.GenerateContentConfig(response_mime_type="application/json")

# ---------------------------------------------------------------------------
# Expanded query pools — rotated round-robin across job rounds
# ---------------------------------------------------------------------------

_ARXIV_QUERY_POOL = [
    "large language model inference serving latency optimization",
    "distributed systems machine learning platform engineering",
    "MLOps observability vector database production deployment",
    "retrieval augmented generation RAG system design architecture",
    "transformer hardware acceleration GPU memory efficiency",
    "autonomous LLM agent framework tool use multi-step reasoning",
    "model quantization pruning compression inference edge",
    "mixture of experts MoE sparse model scaling",
    "reinforcement learning human feedback RLHF alignment tuning",
    "efficient attention sparse transformer long context",
    "diffusion model generation architecture systems engineering",
    "federated learning privacy distributed training optimization",
]

_DDG_QUERY_POOL = [
    "machine learning infrastructure engineering systems 2026",
    "LLM production deployment optimization cost latency",
    "AI agent autonomous framework engineering news",
    "vector database semantic search infrastructure",
    "MLOps GPU cluster distributed training platform",
    "open source AI model serving performance",
    "data engineering pipeline streaming real-time processing",
    "Kubernetes GPU scheduling ML workload orchestration",
    "AI hardware accelerator chip inference systems",
    "developer tools AI assistant coding engineering",
    "eBPF observability kernel systems programming",
    "database performance distributed SQL NoSQL engineering",
]

_ARXIV_PER_QUERY = 6   # papers per arxiv query
_DDG_PER_QUERY   = 7   # articles per DDG query
_ARXIV_PER_ROUND = 4   # arxiv queries per round
_DDG_PER_ROUND   = 3   # DDG queries per round
_MIN_WORDS       = 50  # drop harvested items below this word count


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------


def _gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _extract_retry_delay(err_str: str) -> int:
    """Parse 'retry in Xs' from a 429 error message; default 65 s."""
    match = re.search(r"retry in (\d+)", err_str, re.IGNORECASE)
    return int(match.group(1)) + 5 if match else 65


def _gemini_call(
    client: genai.Client,
    model: str,
    prompt: str,
    max_retries: int = 3,
) -> str:
    """Call Gemini, retrying on 429 RESOURCE_EXHAUSTED with the API-specified delay."""
    for attempt in range(max_retries + 1):
        try:
            resp = client.models.generate_content(
                model=model, contents=prompt, config=_JSON_CFG
            )
            return resp.text or ""
        except Exception as exc:
            err = str(exc)
            if ("429" in err or "RESOURCE_EXHAUSTED" in err) and attempt < max_retries:
                delay = _extract_retry_delay(err)
                logger.warning(
                    "429 rate-limited on %s — retrying in %ds (attempt %d/%d)",
                    model, delay, attempt + 1, max_retries,
                )
                time.sleep(delay)
            else:
                raise
    return ""


def _parse_json_obj(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = (parts[1] if len(parts) > 1 else "").removeprefix("json").strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        return {}


def _parse_json_list(text: str) -> list[Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = (parts[1] if len(parts) > 1 else "").removeprefix("json").strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Phase 1 — Harvest
# ---------------------------------------------------------------------------


def _fetch_arxiv(query: str, max_results: int) -> list[dict[str, Any]]:
    import arxiv  # type: ignore[import-untyped]
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        items: list[dict[str, Any]] = []
        for result in search.results():
            items.append({
                "title":        result.title,
                "url":          result.entry_id,
                "body":         result.summary,
                "author":       ", ".join(str(a) for a in result.authors[:3]),
                "published_at": result.published.isoformat() if result.published else "",
                "source":       "arxiv",
            })
        return items
    except Exception as exc:
        logger.warning("ArXiv fetch failed for %r: %s", query, exc)
        return []


def _fetch_ddg(query: str, max_results: int) -> list[dict[str, Any]]:
    try:
        from ddgs import DDGS
        results = DDGS().news(query, max_results=max_results)
        items: list[dict[str, Any]] = []
        for r in (results or []):
            body = r.get("body") or r.get("excerpt") or ""
            if not body:
                continue
            items.append({
                "title":        r.get("title", ""),
                "url":          r.get("url", r.get("link", "")),
                "body":         body,
                "author":       r.get("source", "Unknown"),
                "published_at": r.get("date", ""),
                "source":       "rss",
            })
        return items
    except Exception as exc:
        logger.warning("DDG fetch failed for %r: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _content_hash(url: str, body: str) -> str:
    return hashlib.sha256((url + body[:1000]).encode()).hexdigest()


def _is_duplicate(conn: sqlite3.Connection, url: str, ch: str) -> bool:
    row = conn.execute(
        "SELECT id FROM generator_documents WHERE url = ? OR content_hash = ?",
        (url, ch),
    ).fetchone()
    return row is not None


def _count_stored(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM generator_documents").fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# Phase 2 — Gatekeeper (BATCHED — one Gemini call for all candidates)
# ---------------------------------------------------------------------------

_BATCH_GATE_PROMPT = """\
You are filtering documents for a senior software engineering knowledge feed.
For each document decide: is it a high-signal technical document?
High-signal means: research papers, system design, engineering deep-dives,
infrastructure, tooling, ML/AI systems, databases, observability, performance.
Low-signal means: shallow news, marketing copy, tutorials for beginners.

Return ONLY a JSON array — one object per document, in the same index order:
[{{"index": 0, "is_high_signal": true, "confidence": 0.85}}, ...]

Documents:
{entries}
"""


def _run_gatekeeper_batch(
    client: genai.Client,
    items: list[dict[str, Any]],
) -> list[MetadataGatekeeperResult | None]:
    """Gate all candidates in ONE Gemini call. Returns one result per item."""
    entries_lines: list[str] = []
    for i, item in enumerate(items):
        excerpt = item.get("body", "")[:300].replace("\n", " ")
        entries_lines.append(
            f"[{i}] source={item.get('source', '?')} | "
            f"title={item.get('title', '')[:120]} | excerpt={excerpt}"
        )
    prompt = _BATCH_GATE_PROMPT.format(entries="\n".join(entries_lines))

    results: list[MetadataGatekeeperResult | None] = [None] * len(items)
    try:
        raw_text = _gemini_call(client, GATEKEEPER_MODEL, prompt)
        entries = _parse_json_list(raw_text)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            idx = entry.get("index")
            if not isinstance(idx, int) or idx < 0 or idx >= len(items):
                continue
            try:
                result = MetadataGatekeeperResult(
                    is_high_signal=bool(entry.get("is_high_signal", False)),
                    confidence=float(entry.get("confidence", 0.0)),
                )
                results[idx] = result if result.passes else None
            except (ValidationError, Exception):
                results[idx] = None
    except Exception as exc:
        logger.warning("Gatekeeper batch call failed: %s", exc)
    return results


# ---------------------------------------------------------------------------
# Phase 3 — Extractor (per-doc, uses _gemini_call with retry built-in)
# ---------------------------------------------------------------------------


def _run_extractor(
    client: genai.Client,
    body: str,
) -> ExtractedDocument | None:
    prompt = build_extractor_prompt(body)
    try:
        raw_text = _gemini_call(client, EXTRACTOR_MODEL, prompt)
        raw = _parse_json_obj(raw_text)
        raw["taxonomy_tags"] = [
            t for t in raw.get("taxonomy_tags", []) if t in TAXONOMY_TAGS
        ] or ["AI Engineering"]
        return ExtractedDocument(**raw)
    except (ValidationError, Exception) as exc:
        logger.warning("Extractor failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Phase 4 — Storage
# ---------------------------------------------------------------------------


def _store_document(
    conn: sqlite3.Connection,
    url: str,
    source: str,
    title: str,
    author: str,
    published_at: str,
    content_hash: str,
    extracted: ExtractedDocument,
    gate_confidence: float,
) -> bool:
    try:
        cursor = conn.execute(
            """
            INSERT INTO generator_documents
                (source, source_id, url, url_hash, content_hash, title, author,
                 published_at, summary, bm25_keywords, taxonomy_tags,
                 image_url, gatekeeper_confidence, processed_at, pipeline_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'complete')
            """,
            (
                source, url, url, _url_hash(url), content_hash,
                title, author, published_at,
                extracted.summary,
                json.dumps(extracted.bm25_keywords),
                json.dumps(extracted.taxonomy_tags),
                extracted.image_url,
                gate_confidence,
                datetime.now(tz=timezone.utc).isoformat(),
            ),
        )
        item_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO generator_fts(rowid, title, keywords, entities) VALUES (?, ?, ?, ?)",
            (
                item_id,
                title,
                " ".join(extracted.bm25_keywords),
                " ".join(extracted.taxonomy_tags),
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError as exc:
        logger.debug("Duplicate insert skipped: %s", exc)
        return False
    except Exception as exc:
        logger.error("Storage error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main job — run until target_docs stored or max_rounds exhausted
# ---------------------------------------------------------------------------


def run_ingestion_job(
    scheduler: Any = None,
    target_docs: int = 20,
    max_rounds: int = 5,
) -> None:
    """
    Full ingestion cycle.  Rotates through query pools across rounds until
    `target_docs` are stored in generator.db or `max_rounds` is exhausted.

    Parameters
    ----------
    scheduler:
        APScheduler instance — used only to update next_run_at in status.
    target_docs:
        Stop early once this many documents are stored.
    max_rounds:
        Hard cap on the number of harvest-gate-extract-store rounds.
    """
    status = AGENT_STATUS["generator"]
    now = datetime.now(tz=timezone.utc).isoformat()
    status.update({
        "state": "running",
        "phase": 1,
        "phase_label": "Harvest",
        "started_at": now,
        "docs_harvested": 0,
        "docs_passed_gate": 0,
        "docs_extracted": 0,
        "docs_stored": 0,
        "docs_skipped": 0,
        "error_message": None,
    })

    try:
        client = _gemini_client()
        conn = sqlite3.connect(db_path())
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")

        seen_urls: set[str] = set()
        arxiv_idx = 0
        ddg_idx = 0

        for round_num in range(max_rounds):
            if status["docs_stored"] >= target_docs:
                logger.info(
                    "Target %d docs reached after %d round(s) — stopping",
                    target_docs, round_num,
                )
                break

            # ── Phase 1: Harvest ────────────────────────────────────────────
            status["phase"] = 1
            status["phase_label"] = "Harvest"
            logger.info("Round %d/%d — harvesting...", round_num + 1, max_rounds)

            raw_items: list[dict[str, Any]] = []
            for _ in range(_ARXIV_PER_ROUND):
                q = _ARXIV_QUERY_POOL[arxiv_idx % len(_ARXIV_QUERY_POOL)]
                arxiv_idx += 1
                raw_items.extend(_fetch_arxiv(q, _ARXIV_PER_QUERY))

            for _ in range(_DDG_PER_ROUND):
                q = _DDG_QUERY_POOL[ddg_idx % len(_DDG_QUERY_POOL)]
                ddg_idx += 1
                raw_items.extend(_fetch_ddg(q, _DDG_PER_QUERY))

            # Dedup + word-count filter
            unique_items: list[dict[str, Any]] = []
            for item in raw_items:
                url  = item.get("url", "")
                body = item.get("body", "")
                if not url or url in seen_urls:
                    status["docs_skipped"] += 1
                    continue
                if len(body.split()) < _MIN_WORDS:
                    status["docs_skipped"] += 1
                    continue
                ch = _content_hash(url, body)
                if _is_duplicate(conn, url, ch):
                    seen_urls.add(url)
                    status["docs_skipped"] += 1
                    continue
                seen_urls.add(url)
                item["_ch"] = ch
                unique_items.append(item)

            status["docs_harvested"] += len(unique_items)
            logger.info("Round %d: %d unique candidates after dedup",
                        round_num + 1, len(unique_items))

            if not unique_items:
                logger.info("No new content in round %d — trying next round",
                            round_num + 1)
                continue

            # ── Phase 2: Gatekeeper (one batched Gemini call) ───────────────
            status["phase"] = 2
            status["phase_label"] = "Gatekeeper"
            gate_results = _run_gatekeeper_batch(client, unique_items)

            passed = sum(1 for g in gate_results if g is not None)
            logger.info("Round %d: gatekeeper passed %d/%d",
                        round_num + 1, passed, len(unique_items))

            # ── Phases 3 + 4: per-doc extract & store ───────────────────────
            for item, gate in zip(unique_items, gate_results):
                if gate is None:
                    status["docs_skipped"] += 1
                    continue
                status["docs_passed_gate"] += 1

                status["phase"] = 3
                status["phase_label"] = "Extractor"
                extracted = _run_extractor(client, item.get("body", ""))
                if extracted is None:
                    status["docs_skipped"] += 1
                    continue
                status["docs_extracted"] += 1

                status["phase"] = 4
                status["phase_label"] = "Storage"
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
                    status["docs_stored"] += 1
                    logger.info("Stored doc %d/%d: %s",
                                status["docs_stored"], target_docs,
                                item.get("title", "")[:60])
                    if status["docs_stored"] >= target_docs:
                        logger.info("Target %d reached — stopping early", target_docs)
                        break  # inner loop break

            if status["docs_stored"] >= target_docs:
                break  # outer loop break

        conn.close()
        finish = datetime.now(tz=timezone.utc).isoformat()
        status.update({
            "state": "success",
            "phase": None,
            "phase_label": None,
            "finished_at": finish,
            "last_run_at": finish,
        })
        logger.info(
            "Ingestion done — harvested=%d passed_gate=%d extracted=%d stored=%d",
            status["docs_harvested"],
            status["docs_passed_gate"],
            status["docs_extracted"],
            status["docs_stored"],
        )

    except Exception as exc:
        logger.error("Ingestion job failed: %s", exc, exc_info=True)
        status.update({
            "state": "error",
            "phase": None,
            "phase_label": None,
            "finished_at": datetime.now(tz=timezone.utc).isoformat(),
            "error_message": str(exc)[:300],
        })

    finally:
        if scheduler:
            job = scheduler.get_job("ingestion")
            if job and getattr(job, "next_run_time", None):
                status["next_run_at"] = job.next_run_time.isoformat()
