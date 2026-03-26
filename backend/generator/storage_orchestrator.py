"""
Storage Orchestrator Agent
--------------------------
Receives a validated FlashTaggerOutput, persists the generated image asset,
generates a semantic embedding, and inserts the complete document record
into PostgreSQL — entirely through MCP tool calls.

No raw SQL is written here.  All database interaction is delegated to the
`storage_server` MCP process via the MCPClient stdio transport.

Workflow
--------
1. VALIDATE   — Pydantic ensures all required fields are present before any
                tool call is made.  trend_density_score → trend_score mapping
                happens here.
2. ASSET      — If an image was supplied (base64 + filename), call
                `save_asset_locally` and record the returned path.
3. EMBED      — Build the embed text (summary + keywords) and call
                `generate_embedding`.  Halt on failure — do not insert
                a document without an embedding.
4. STORE      — Assemble the final payload and call `pg_insert_document`.
5. CONFIRM    — Return a StorageConfirmation with the new document ID or
                a structured error.

Usage
-----
    agent = StorageOrchestratorAgent()
    result = agent.orchestrate(flash_output, raw_text="…")
    if result.success:
        print(result.document_id)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from .mcp_client import MCPClient, MCPError
from .schemas import FlashTaggerOutput, StorageConfirmation

logger = logging.getLogger(__name__)

_SERVER_MODULE = "backend.mcp_servers.storage_server"


def _server_cmd() -> list[str]:
    return [sys.executable, "-m", _SERVER_MODULE]


def _embed_text(flash: FlashTaggerOutput) -> str:
    """Combine summary and keywords into a single string for embedding."""
    kw_line = " | ".join(flash.keywords)
    return f"{flash.summary}\n{kw_line}"


def _build_pg_payload(
    flash: FlashTaggerOutput,
    raw_text: str,
    image_local_path: str,
    embedding: list[float],
) -> dict[str, Any]:
    """Assemble the exact schema expected by pg_insert_document."""
    return {
        "original_text":     raw_text,
        "summary":           flash.summary,
        "keywords":          flash.keywords,
        "trend_score":       flash.trend_density_score,   # field rename here
        "matched_trends":    flash.matched_trends,
        "image_prompt":      flash.image_prompt,
        "image_local_path":  image_local_path,
        "content_embedding": embedding,
    }


class StorageOrchestratorAgent:
    """
    Deterministic workflow agent — no LLM loop.
    Calls three MCP tools in strict sequence to persist a document.
    """

    def orchestrate(
        self,
        flash_output: FlashTaggerOutput,
        raw_text: str,
    ) -> StorageConfirmation:
        """
        Run the full storage workflow for one Flash Tagger payload.

        Parameters
        ----------
        flash_output:
            Validated output from the Flash Tagger Agent.
        raw_text:
            The original document body before summarisation.
        """
        env = {**os.environ}

        try:
            with MCPClient(_server_cmd(), env) as storage:
                image_path = self._step_save_asset(storage, flash_output)
                embedding = self._step_embed(storage, flash_output)
                if embedding is None:
                    return StorageConfirmation(
                        success=False,
                        error="Embedding generation failed — document not inserted.",
                    )
                document_id = self._step_insert(
                    storage, flash_output, raw_text, image_path, embedding
                )
                return StorageConfirmation(
                    success=True,
                    document_id=document_id,
                    image_local_path=image_path,
                )
        except MCPError as exc:
            logger.error("StorageOrchestrator MCP error: %s", exc)
            return StorageConfirmation(success=False, error=str(exc))
        except Exception as exc:
            logger.error("StorageOrchestrator unexpected error: %s", exc)
            return StorageConfirmation(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Step 1 — Asset
    # ------------------------------------------------------------------

    def _step_save_asset(
        self, storage: MCPClient, flash: FlashTaggerOutput
    ) -> str:
        """Save image if provided; return local path or empty string."""
        if not flash.image_filename or not flash.image_binary_b64:
            logger.debug("No image supplied — skipping save_asset_locally")
            return ""

        result = storage.call("save_asset_locally", {
            "filename":    flash.image_filename,
            "binary_data": flash.image_binary_b64,
        })
        path: str = result.get("path", "")
        logger.info("Asset saved: %s", path)
        return path

    # ------------------------------------------------------------------
    # Step 2 — Embed
    # ------------------------------------------------------------------

    def _step_embed(
        self, storage: MCPClient, flash: FlashTaggerOutput
    ) -> list[float] | None:
        """Generate embedding; return None if the tool reports failure."""
        text = _embed_text(flash)
        result = storage.call("generate_embedding", {"text": text})
        embedding: list[float] | None = result.get("embedding")

        if not embedding:
            logger.error(
                "generate_embedding returned empty vector for summary: %.80s…", flash.summary
            )
            return None

        logger.info("Embedding ready: %d dims", len(embedding))
        return embedding

    # ------------------------------------------------------------------
    # Step 3 — Insert
    # ------------------------------------------------------------------

    def _step_insert(
        self,
        storage: MCPClient,
        flash: FlashTaggerOutput,
        raw_text: str,
        image_path: str,
        embedding: list[float],
    ) -> int:
        """Insert via pg_insert_document and return the new document ID."""
        payload = _build_pg_payload(flash, raw_text, image_path, embedding)
        result = storage.call("pg_insert_document", payload)
        document_id: int = result["document_id"]
        logger.info("Document stored: id=%d", document_id)
        return document_id
