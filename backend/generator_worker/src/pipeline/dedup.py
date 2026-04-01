"""
Stage 2 (programmatic): Deduplication — checks PostgreSQL for an existing url_hash
before any LLM call is made.

Fail-open policy: if the MCP call errors, we return False (allow through) so we
never silently drop a document due to an infra hiccup.
"""

from __future__ import annotations

import hashlib
import logging

from src.storage.mcp_client import MCPClient, MCPError

logger = logging.getLogger(__name__)


def compute_url_hash(url: str) -> str:
    """SHA-256 hex digest of the raw URL string."""
    return hashlib.sha256(url.encode()).hexdigest()


def is_duplicate(url: str, mcp: MCPClient) -> bool:
    """
    Query PostgreSQL via the MCP SQL tool to check whether a document with the
    given URL has already been stored.

    Returns:
        True  — document already exists; pipeline should skip it.
        False — document is new (or MCP errored; fail-open).

    On any MCPError or unexpected exception a warning is logged and the function
    returns False so the document is re-processed rather than silently lost.
    """
    url_hash = compute_url_hash(url)
    try:
        result = mcp.call(
            "execute_query",
            {
                "query": "SELECT 1 FROM generator_documents WHERE url_hash = $1 LIMIT 1",
                "params": [url_hash],
            },
        )
        # result is expected to be {"rows": [...]} where rows is a list
        rows: list[object] = result.get("rows", [])
        exists = len(rows) > 0
        if exists:
            logger.debug("Dedup: url_hash=%s already in DB, skipping.", url_hash)
        return exists
    except MCPError as exc:
        logger.warning(
            "Dedup MCP error for url_hash=%s: %s — failing open (allowing through).",
            url_hash,
            exc,
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Dedup unexpected error for url_hash=%s: %s — failing open.",
            url_hash,
            exc,
        )
        return False
