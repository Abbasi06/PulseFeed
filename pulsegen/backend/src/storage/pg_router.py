"""
Stage 5: PostgreSQL storage router — orchestrates two sequential MCP tool calls
(generate_embedding → pg_insert_document) to persist a processed document.

A missing or empty embedding is treated as fatal; all other exceptions are caught
and surfaced via StorageConfirmation so the Celery task layer decides retry policy.
"""

from __future__ import annotations

import logging

from src.config import settings
from src.schemas import StorageConfirmation, StoragePayload
from src.storage.mcp_client import MCPClient

logger = logging.getLogger(__name__)


def _mcp_env() -> dict[str, str]:
    """Build env vars for the MCP storage subprocess."""
    import os

    env = dict(os.environ)
    env["LLM_EMBED_URL"] = settings.llm_embed_url
    env["LLM_API_KEY"] = settings.llm_api_key
    env["STORAGE_DATABASE_URL"] = settings.storage_database_url
    return env


def route_to_postgres(payload: StoragePayload) -> StorageConfirmation:
    """
    Persist a fully-processed document to PostgreSQL via two MCP tool calls.

    Step 1 — generate_embedding
        Concatenates summary + space + space-joined BM25 keywords, sends to the
        embedding model, and expects {"embedding": [... 768 floats ...]}.
        A missing or empty embedding list raises RuntimeError (fatal — a document
        without a vector cannot be stored).

    Step 2 — pg_insert_document
        Inserts all StoragePayload fields plus the embedding vector.
        published_at is serialised as an ISO-8601 string (or None).
        bm25_keywords and taxonomy_tags are passed as plain Python lists;
        the MCP server handles JSON serialisation for PostgreSQL array columns.
        Expects {"document_id": "<uuid>"}.

    Returns:
        StorageConfirmation(success=True, document_id=<uuid>) on success.
        StorageConfirmation(success=False, error=<message>)  on any exception,
        so the caller can decide whether to retry.

    Uses MCPClient as a context manager with settings.mcp_storage_command so
    the subprocess is always cleaned up regardless of outcome.
    """
    try:
        with MCPClient(settings.mcp_storage_command, env=_mcp_env()) as mcp:
            # ── Step 1: Generate embedding ───────────────────────────────────
            embedding_input = (
                payload.summary + " " + " ".join(payload.bm25_keywords)
            )
            embed_result = mcp.call(
                "generate_embedding",
                {
                    "text": embedding_input,
                    "model": settings.embedding_model,
                },
            )

            embedding: list[float] = embed_result.get("embedding", [])
            if not embedding:
                raise RuntimeError(
                    f"generate_embedding returned empty vector for url_hash="
                    f"{payload.url_hash!r} — cannot store document without vector."
                )

            logger.debug(
                "Embedding generated: %d dims for url_hash=%s",
                len(embedding),
                payload.url_hash,
            )

            # ── Step 2: Insert document into PostgreSQL ───────────────────────
            insert_args: dict[str, object] = {
                "source": payload.source.value,
                "source_id": payload.source_id,
                "url": payload.url,
                "url_hash": payload.url_hash,
                "content_hash": payload.content_hash,
                "title": payload.title,
                "author": payload.author,
                "published_at": (
                    payload.published_at.isoformat() if payload.published_at else None
                ),
                "summary": payload.summary,
                "bm25_keywords": payload.bm25_keywords,
                "taxonomy_tags": [str(t) for t in payload.taxonomy_tags],
                "image_url": payload.image_url,
                "gatekeeper_confidence": payload.gatekeeper_confidence,
                "embedding": embedding,
                "pipeline_status": payload.pipeline_status,
                "processed_at": payload.processed_at.isoformat(),
            }

            insert_result = mcp.call("pg_insert_document", insert_args)

            document_id: str | None = insert_result.get("document_id")
            if not document_id:
                raise RuntimeError(
                    "pg_insert_document did not return a document_id. "
                    f"Response was: {insert_result!r}"
                )

            logger.info(
                "Stored document document_id=%s url_hash=%s",
                document_id,
                payload.url_hash,
            )
            return StorageConfirmation(success=True, document_id=document_id)

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "pg_router failed for url_hash=%s: %s",
            payload.url_hash,
            exc,
            exc_info=True,
        )
        return StorageConfirmation(success=False, error=str(exc))
