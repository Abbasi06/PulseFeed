from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from .db import db_path
from .mcp_client import MCPClient, MCPError
from .prompts import build_extractor_prompt, build_gatekeeper_prompt
from .schemas import (
    DataSource,
    ExtractedDocument,
    MetadataGatekeeperResult,
    RawDocument,
    StoragePayload,
)

logger = logging.getLogger(__name__)

GATEKEEPER_MODEL = "gemini-2.5-flash-lite"
EXTRACTOR_MODEL = "gemini-2.5-flash"
_JSON_CONFIG = types.GenerateContentConfig(response_mime_type="application/json")

# Paths to MCP servers (resolved relative to this file's parent's parent = backend/)
_BACKEND_DIR = Path(__file__).parent.parent


def _get_server_cmd(module: str) -> list[str]:
    return [sys.executable, "-m", module]


def _gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _parse_gemini_json(text: str, context: str) -> dict[str, Any]:
    """Strip markdown fences and parse JSON from Gemini output."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        inner = parts[1] if len(parts) > 1 else ""
        text = inner.removeprefix("json").strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result  # type: ignore[return-value]
        logger.warning("Gemini returned non-dict for %s", context)
        return {}
    except json.JSONDecodeError as exc:
        logger.warning("Gemini invalid JSON for %s: %s", context, exc)
        return {}


class GeneratorAgent:
    """Synchronous agent that orchestrates the Inference Cascade phases."""

    def __init__(self) -> None:
        self._client = _gemini_client()

    # ------------------------------------------------------------------
    # Phase 1: Harvest
    # ------------------------------------------------------------------

    def harvest(self, source: str, query: str, max_results: int = 20) -> list[RawDocument]:
        """Call mcp-search-tool + mcp-sql-tool; return deduplicated RawDocuments."""
        env = {**os.environ, "DATABASE_PATH": db_path()}
        docs: list[RawDocument] = []

        with (
            MCPClient(_get_server_cmd("backend.mcp_servers.search_server"), env) as search,
            MCPClient(_get_server_cmd("backend.mcp_servers.sql_server"), env) as sql,
        ):
            result = search.call(
                "search",
                {"query": query, "source": source, "max_results": max_results},
            )
            items: list[dict[str, Any]] = result.get("items", [])
            logger.info("Harvested %d raw items from %s", len(items), source)

            for item in items:
                doc = _build_raw_doc(item, source)
                if doc is None:
                    continue
                if _is_duplicate(sql, doc):
                    continue
                docs.append(doc)

        logger.info("Phase 1 complete: %d unique docs from %s", len(docs), source)
        return docs

    # ------------------------------------------------------------------
    # Phase 2: Gatekeeper
    # ------------------------------------------------------------------

    def gatekeeper(self, doc: RawDocument) -> MetadataGatekeeperResult | None:
        """Call gemini-2.5-flash-lite to classify doc metadata. Returns None if discarded."""
        prompt = build_gatekeeper_prompt(doc.title, doc.author, doc.source.value, doc.body)
        try:
            response = self._client.models.generate_content(
                model=GATEKEEPER_MODEL,
                contents=prompt,
                config=_JSON_CONFIG,
            )
            raw = _parse_gemini_json(response.text or "", context=f"gatekeeper:{doc.url}")
            result = MetadataGatekeeperResult(**raw)
        except (ValidationError, Exception) as exc:
            logger.warning("Gatekeeper error for %r — discarding: %s", doc.title, exc)
            return None

        if not result.passes:
            logger.debug(
                "Gatekeeper rejected (high_signal=%s, conf=%.2f): %s",
                result.is_high_signal,
                result.confidence,
                doc.title,
            )
            return None

        logger.info("Gatekeeper passed (conf=%.2f): %s", result.confidence, doc.title)
        return result

    # ------------------------------------------------------------------
    # Phase 3: Deep Extractor
    # ------------------------------------------------------------------

    def extract(self, doc: RawDocument, max_retries: int = 2) -> ExtractedDocument | None:
        """Call gemini-2.5-flash to extract summary, keywords, taxonomy. Returns None on failure."""
        prompt = build_extractor_prompt(doc.body)
        last_error: str = ""

        for attempt in range(max_retries + 1):
            extracted = self._extract_attempt(doc, prompt, attempt, last_error, max_retries)
            if isinstance(extracted, ExtractedDocument):
                return extracted
            last_error = extracted  # str error message

        logger.error("Extractor failed after %d attempts for: %s", max_retries + 1, doc.title)
        return None

    def _extract_attempt(
        self,
        doc: RawDocument,
        prompt: str,
        attempt: int,
        last_error: str,
        max_retries: int,
    ) -> ExtractedDocument | str:
        """Single extraction attempt. Returns ExtractedDocument on success or error string."""
        retry_hint = (
            f"\n\nPrevious attempt failed: {last_error}. Please fix and retry."
            if attempt > 0
            else ""
        )
        try:
            response = self._client.models.generate_content(
                model=EXTRACTOR_MODEL,
                contents=prompt + retry_hint,
                config=_JSON_CONFIG,
            )
            raw = _parse_gemini_json(response.text or "", context=f"extractor:{doc.url}")
            return ExtractedDocument(**raw)
        except ValidationError as exc:
            logger.warning(
                "Extractor validation error (attempt %d/%d): %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
            return str(exc)
        except Exception as exc:
            logger.warning(
                "Extractor error (attempt %d/%d): %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
            return str(exc)

    # ------------------------------------------------------------------
    # Phase 4: Storage Router
    # ------------------------------------------------------------------

    def store(
        self,
        doc: RawDocument,
        extracted: ExtractedDocument,
        gatekeeper_confidence: float,
    ) -> StoragePayload:
        """Insert into SQLite via mcp-sql-tool, embed+upsert via mcp-vector-tool."""
        payload = StoragePayload(
            source=doc.source,
            source_id=doc.url,
            url=doc.url,
            title=doc.title,
            author=doc.author,
            published_at=doc.published_at,
            content_hash=doc.content_hash,
            summary=extracted.summary,
            bm25_keywords=extracted.bm25_keywords,
            taxonomy_tags=extracted.taxonomy_tags,
            image_url=extracted.image_url,
            gatekeeper_confidence=gatekeeper_confidence,
            processed_at=datetime.now(tz=timezone.utc),
        )

        env = {**os.environ, "DATABASE_PATH": db_path()}
        with (
            MCPClient(_get_server_cmd("backend.mcp_servers.sql_server"), env) as sql,
            MCPClient(_get_server_cmd("backend.mcp_servers.vector_server"), env) as vector,
        ):
            payload = _insert_relational(sql, payload)
            if payload.item_id is not None:
                payload = _insert_fts(sql, payload)
                payload = _upsert_vector(vector, payload)

        logger.info(
            "Stored item_id=%s, embedding=%s: %s",
            payload.item_id,
            payload.embedding_id,
            payload.title,
        )
        return payload


# ------------------------------------------------------------------
# Private helpers (kept outside class to enforce <40-line methods)
# ------------------------------------------------------------------


def _build_raw_doc(item: dict[str, Any], source: str) -> RawDocument | None:
    """Construct a RawDocument from a raw search result dict; return None if invalid."""
    try:
        return RawDocument(
            title=item.get("title", ""),
            url=item.get("url", ""),
            body=item.get("body", ""),
            author=item.get("author", "Unknown"),
            published_at=item.get("published_at", ""),
            source=DataSource(source),
        )
    except (ValueError, Exception) as exc:
        logger.warning("Heuristic filter dropped item %r: %s", item.get("title"), exc)
        return None


def _is_duplicate(sql: MCPClient, doc: RawDocument) -> bool:
    """Return True if this URL or content_hash already exists in generator_documents."""
    dedup = sql.call("query", {
        "sql": "SELECT id FROM generator_documents WHERE url = ? OR content_hash = ?",
        "params": [doc.url, doc.content_hash],
    })
    if dedup.get("row_count", 0) > 0:
        logger.debug("Duplicate skipped: %s", doc.url)
        return True
    return False


def _insert_relational(sql: MCPClient, payload: StoragePayload) -> StoragePayload:
    """INSERT the document row; mutate and return payload with item_id set."""
    sql_result = sql.call("execute", {
        "sql": """
            INSERT INTO generator_documents
                (source, source_id, url, content_hash, title, author,
                 published_at, summary, bm25_keywords, taxonomy_tags,
                 image_url, gatekeeper_confidence, processed_at, pipeline_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'complete')
        """,
        "params": [
            payload.source.value, payload.source_id, payload.url,
            payload.content_hash, payload.title, payload.author,
            payload.published_at, payload.summary,
            json.dumps(payload.bm25_keywords),
            json.dumps(payload.taxonomy_tags),
            payload.image_url, payload.gatekeeper_confidence,
            payload.processed_at.isoformat(),
        ],
    })
    payload.item_id = sql_result.get("last_insert_id")
    return payload


def _insert_fts(sql: MCPClient, payload: StoragePayload) -> StoragePayload:
    """INSERT into FTS5 sparse index; mutate and return payload with fts_rowid set."""
    sql.call("execute", {
        "sql": "INSERT INTO generator_fts(rowid, title, keywords, entities) VALUES (?, ?, ?, ?)",
        "params": [
            payload.item_id,
            payload.title,
            " ".join(payload.bm25_keywords),
            " ".join(payload.taxonomy_tags),
        ],
    })
    payload.fts_rowid = payload.item_id
    return payload


def _upsert_vector(vector: MCPClient, payload: StoragePayload) -> StoragePayload:
    """Upsert embedding via mcp-vector-tool; failures are non-fatal."""
    try:
        vector.call("upsert", {
            "id": str(payload.item_id),
            "text": payload.summary,
            "metadata": {
                "taxonomy_tags": payload.taxonomy_tags,
                "source": payload.source.value,
                "published_at": payload.published_at,
                "title": payload.title,
                "url": payload.url,
            },
        })
        payload.embedding_id = str(payload.item_id)
    except MCPError as exc:
        logger.error(
            "Vector upsert failed for item_id=%d — embedding_id=NULL: %s",
            payload.item_id,
            exc,
        )
    return payload
