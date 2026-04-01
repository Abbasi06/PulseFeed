"""
PG Search MCP Server
--------------------
Exposes three tools to the Two-Stage Recommender over stdio JSON-RPC 2.0:

  pg_hybrid_search      — semantic + BM25 + trend-score hybrid retrieval
  record_interaction    — persist a user interaction event
  get_feedback_history  — fetch bucketed interaction history for a user

Environment variables (read at startup):
  STORAGE_DATABASE_URL  PostgreSQL DSN, e.g. postgresql://user:pass@host:5432/db

Launch:
  uv run python -m backend.mcp_servers.pg_search_server
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool manifest
# ---------------------------------------------------------------------------

TOOLS_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "pg_hybrid_search",
        "description": "Hybrid semantic + BM25 + trend-score search over the documents table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query_embedding": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "768-dim query vector",
                },
                "keyword_query": {"type": "string", "description": "BM25 text query"},
                "alpha": {"type": "number", "default": 0.4, "description": "Semantic weight"},
                "beta":  {"type": "number", "default": 0.3, "description": "Keyword weight"},
                "gamma": {"type": "number", "default": 0.3, "description": "Trend weight"},
                "top_k": {"type": "integer", "default": 50, "maximum": 100},
                "taxonomy_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional matched_trends filter",
                },
            },
            "required": ["query_embedding", "keyword_query"],
        },
    },
    {
        "name": "record_interaction",
        "description": "Persist a user interaction event (like, click, skip, read_complete).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id":     {"type": "integer"},
                "document_id": {"type": "integer"},
                "action": {
                    "type": "string",
                    "enum": ["like", "click", "skip", "read_complete"],
                },
            },
            "required": ["user_id", "document_id", "action"],
        },
    },
    {
        "name": "get_feedback_history",
        "description": "Fetch the last 500 interactions for a user, bucketed by action.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
            },
            "required": ["user_id"],
        },
    },
]

# ---------------------------------------------------------------------------
# Module-level connection (set in _bootstrap)
# ---------------------------------------------------------------------------

_conn: Any = None  # psycopg2 connection

_INTERACTIONS_DDL = """
CREATE TABLE IF NOT EXISTS user_interactions (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    document_id   INTEGER NOT NULL,
    action        TEXT NOT NULL,
    interacted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ui_user_id ON user_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_ui_doc_id  ON user_interactions(document_id);
"""

_HYBRID_SQL = """
SELECT
    d.id,
    d.title,
    d.summary,
    d.keywords,
    d.trend_score,
    d.matched_trends,
    d.image_local_path,
    d.image_prompt,
    (
        %s * (1.0 - (d.content_embedding <=> %s::vector))
      + %s * COALESCE(
            ts_rank(
                to_tsvector('english',
                    COALESCE(d.summary, '') || ' ' ||
                    array_to_string(d.keywords, ' ')
                ),
                plainto_tsquery('english', %s)
            ), 0.0
        )
      + %s * COALESCE(d.trend_score, 0.0)
    ) AS final_score
FROM documents d
WHERE d.content_embedding IS NOT NULL
  AND (%s::text[] IS NULL OR d.matched_trends && %s::text[])
ORDER BY final_score DESC
LIMIT %s
"""


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


def _bootstrap() -> None:
    """Connect to PostgreSQL and ensure user_interactions table exists."""
    global _conn  # noqa: PLW0603

    database_url = os.environ.get("STORAGE_DATABASE_URL", "")
    if not database_url:
        logger.warning("STORAGE_DATABASE_URL not set — database tools will fail at call time")
        return

    try:
        import psycopg2
        from pgvector.psycopg2 import register_vector

        _conn = psycopg2.connect(database_url)
        _conn.autocommit = True
        register_vector(_conn)

        with _conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            for statement in _INTERACTIONS_DDL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    cur.execute(stmt)

        logger.info("PostgreSQL pg_search tables ready")
    except Exception as exc:
        logger.warning("PostgreSQL bootstrap warning: %s", exc)


# ---------------------------------------------------------------------------
# Tool: pg_hybrid_search
# ---------------------------------------------------------------------------


def _tool_pg_hybrid_search(arguments: dict[str, Any]) -> dict[str, Any]:
    if _conn is None:
        return _err("Database not configured")

    try:
        import numpy as np

        query_embedding: list[float] = arguments["query_embedding"]
        keyword_query: str = arguments["keyword_query"]
        alpha: float = float(arguments.get("alpha", 0.4))
        beta: float = float(arguments.get("beta", 0.3))
        gamma: float = float(arguments.get("gamma", 0.3))
        top_k: int = min(int(arguments.get("top_k", 50)), 100)
        taxonomy_filter: list[str] | None = arguments.get("taxonomy_filter") or None

        embedding_vec = np.array(query_embedding, dtype=np.float32)
        embedding_str = str(list(embedding_vec))

        params = (
            alpha, embedding_str,
            beta, keyword_query,
            gamma,
            taxonomy_filter, taxonomy_filter,
            top_k,
        )

        with _conn.cursor() as cur:
            cur.execute(_HYBRID_SQL, params)
            rows = cur.fetchall()

        documents = [_row_to_doc(r) for r in rows]
        logger.info("pg_hybrid_search returned %d documents", len(documents))
        return {"documents": documents}
    except Exception as exc:
        return _err(f"pg_hybrid_search failed: {exc}")


def _row_to_doc(r: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id":               r[0],
        "title":            r[1],
        "summary":          r[2],
        "keywords":         list(r[3] or []),
        "trend_score":      float(r[4] or 0),
        "matched_trends":   list(r[5] or []),
        "image_local_path": r[6] or "",
        "final_score":      float(r[8]),
    }


# ---------------------------------------------------------------------------
# Tool: record_interaction
# ---------------------------------------------------------------------------


def _tool_record_interaction(arguments: dict[str, Any]) -> dict[str, Any]:
    if _conn is None:
        return _err("Database not configured")

    try:
        user_id: int = int(arguments["user_id"])
        document_id: int = int(arguments["document_id"])
        action: str = arguments["action"]

        with _conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_interactions (user_id, document_id, action) VALUES (%s, %s, %s)",
                (user_id, document_id, action),
            )

        logger.info("Interaction recorded: user_id=%d doc_id=%d action=%s", user_id, document_id, action)
        return {"recorded": True}
    except Exception as exc:
        return _err(f"record_interaction failed: {exc}")


# ---------------------------------------------------------------------------
# Tool: get_feedback_history
# ---------------------------------------------------------------------------

_ACTION_MAP: dict[str, str] = {
    "like":          "liked",
    "click":         "clicked",
    "skip":          "ignored",
    "read_complete": "read_complete",
}


def _tool_get_feedback_history(arguments: dict[str, Any]) -> dict[str, Any]:
    if _conn is None:
        return _err("Database not configured")

    try:
        user_id: int = int(arguments["user_id"])

        with _conn.cursor() as cur:
            cur.execute(
                "SELECT document_id, action FROM user_interactions "
                "WHERE user_id = %s ORDER BY interacted_at DESC LIMIT 500",
                (user_id,),
            )
            rows = cur.fetchall()

        buckets: dict[str, list[int]] = {
            "liked": [], "clicked": [], "ignored": [], "read_complete": []
        }
        for doc_id, action in rows:
            bucket_key = _ACTION_MAP.get(action)
            if bucket_key is not None:
                buckets[bucket_key].append(int(doc_id))

        logger.info("Feedback history fetched for user_id=%d (%d rows)", user_id, len(rows))
        return buckets
    except Exception as exc:
        return _err(f"get_feedback_history failed: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _err(message: str) -> dict[str, Any]:
    logger.error(message)
    return {"error": message}


# ---------------------------------------------------------------------------
# JSON-RPC dispatch
# ---------------------------------------------------------------------------

_TOOL_HANDLERS: dict[str, Any] = {
    "pg_hybrid_search":    _tool_pg_hybrid_search,
    "record_interaction":  _tool_record_interaction,
    "get_feedback_history": _tool_get_feedback_history,
}


def _handle_tools_list(request_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS_MANIFEST}}


def _handle_tools_call(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name: str = params.get("name", "")
    arguments: dict[str, Any] = params.get("arguments", {})
    handler = _TOOL_HANDLERS.get(name)

    if handler is None:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown tool: {name}"},
        }

    result = handler(arguments)

    if "error" in result:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": result["error"]},
        }

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    method: str = request.get("method", "")
    params: dict[str, Any] = request.get("params", {})

    if method == "tools/list":
        return _handle_tools_list(request_id)
    if method == "tools/call":
        return _handle_tools_call(request_id, params)

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(levelname)s  pg_search_server  %(message)s",
    )
    _bootstrap()
    logger.info("PG Search MCP server ready — listening on stdin")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except Exception as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
