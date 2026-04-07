"""
Retriever Agent — Stage 1 of the Two-Stage Recommender
-------------------------------------------------------
Translates a UserProfile into a 768-dim query embedding, executes a hybrid
search (semantic + BM25 + trend score weighting), and returns the top-50
candidate document pool for the Validator Node.

Hybrid score formula:
    Final = α·SemanticSimilarity + β·KeywordRank + γ·TrendScore
            (α=0.4, β=0.3, γ=0.3 by default)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from openai import OpenAI

from .mcp_client import MCPClient
from .schemas import CandidateDocument, UserProfile

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "nomic-embed-text"
_EMBED_URL = os.environ.get("LLM_EMBED_URL", "http://host.docker.internal:8082/v1")
_API_KEY = os.environ.get("LLM_API_KEY", "local")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _get_server_cmd(module: str) -> list[str]:
    return [sys.executable, "-m", module]


def _build_keyword_query(profile: UserProfile) -> str:
    """Combine field and first five subfields into a BM25 keyword query."""
    parts = [profile.field] + profile.subfields[:5]
    return " ".join(parts)


# ---------------------------------------------------------------------------
# RetrieverAgent
# ---------------------------------------------------------------------------


class RetrieverAgent:
    """Synchronous Stage-1 retriever: profile → embedding → hybrid search → candidates."""

    def __init__(self) -> None:
        self._client = OpenAI(base_url=_EMBED_URL, api_key=_API_KEY)

    def retrieve(
        self,
        profile: UserProfile,
        alpha: float = 0.4,
        beta: float = 0.3,
        gamma: float = 0.3,
        top_k: int = 50,
        taxonomy_filter: list[str] | None = None,
    ) -> list[CandidateDocument]:
        """Full retrieval pipeline: embed profile → hybrid search → return candidates."""
        query_embedding = self._embed_profile(profile)
        keyword_query = _build_keyword_query(profile)
        return self._search(
            query_embedding, keyword_query, alpha, beta, gamma, top_k, taxonomy_filter
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _embed_profile(self, profile: UserProfile) -> list[float]:
        """Embed the user profile into a 768-dim query vector via Ollama."""
        profile_text = (
            f"{profile.field}. "
            f"{' '.join(profile.subfields)}. "
            f"{' '.join(profile.recent_search_history[:5])}"
        )
        response = self._client.embeddings.create(
            model=_EMBEDDING_MODEL,
            input=profile_text,
        )
        values: list[float] = response.data[0].embedding
        logger.info(
            "Profile embedded: user_id=%d, dims=%d", profile.user_id, len(values)
        )
        return values

    def _search(
        self,
        query_embedding: list[float],
        keyword_query: str,
        alpha: float,
        beta: float,
        gamma: float,
        top_k: int,
        taxonomy_filter: list[str] | None,
    ) -> list[CandidateDocument]:
        """Call pg_hybrid_search via MCP and map results to CandidateDocument."""
        env: dict[str, str] = {**os.environ}
        arguments: dict[str, Any] = {
            "query_embedding":  query_embedding,
            "keyword_query":    keyword_query,
            "alpha":            alpha,
            "beta":             beta,
            "gamma":            gamma,
            "top_k":            top_k,
        }
        if taxonomy_filter is not None:
            arguments["taxonomy_filter"] = taxonomy_filter

        cmd = _get_server_cmd("mcp_servers.pg_search_server")
        with MCPClient(cmd, env) as client:
            result = client.call("pg_hybrid_search", arguments)

        docs_raw: list[dict[str, Any]] = result.get("documents", [])
        candidates = [CandidateDocument(**doc) for doc in docs_raw]
        logger.info("pg_hybrid_search returned %d candidates", len(candidates))
        return candidates
