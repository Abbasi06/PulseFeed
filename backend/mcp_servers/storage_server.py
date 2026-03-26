"""
Storage MCP Server
------------------
Exposes three tools to the Storage Orchestrator Agent over stdio JSON-RPC 2.0:

  save_asset_locally   — writes a base64-encoded image to ./assets/images/
  generate_embedding   — calls Gemini text-embedding-004 (768 dims)
  pg_insert_document   — inserts a fully-processed document into PostgreSQL
                         with a pgvector content_embedding column

Environment variables (all read at startup):
  GEMINI_API_KEY        required for generate_embedding
  STORAGE_DATABASE_URL  PostgreSQL DSN, e.g. postgresql://user:pass@host:5432/db
  ASSETS_DIR            override for the asset root (default: ./assets/images)

Launch:
  uv run python -m backend.mcp_servers.storage_server
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool manifest
# ---------------------------------------------------------------------------

TOOLS_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "save_asset_locally",
        "description": "Save a base64-encoded image file to ./assets/images/ and return its relative path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename":    {"type": "string"},
                "binary_data": {"type": "string", "description": "Base64-encoded file content"},
            },
            "required": ["filename", "binary_data"],
        },
    },
    {
        "name": "generate_embedding",
        "description": "Embed text with Gemini text-embedding-004 (768 dims) and return a float array.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "pg_insert_document",
        "description": "Insert a fully processed document and its pgvector embedding into PostgreSQL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "original_text":      {"type": "string"},
                "summary":            {"type": "string"},
                "keywords":           {"type": "array", "items": {"type": "string"}},
                "trend_score":        {"type": "number"},
                "matched_trends":     {"type": "array", "items": {"type": "string"}},
                "image_prompt":       {"type": "string"},
                "image_local_path":   {"type": "string"},
                "content_embedding":  {"type": "array", "items": {"type": "number"}},
            },
            "required": ["original_text", "summary", "content_embedding"],
        },
    },
]

# ---------------------------------------------------------------------------
# Startup: assets directory + PostgreSQL table
# ---------------------------------------------------------------------------

_ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", "./assets/images"))
_DATABASE_URL = os.environ.get("STORAGE_DATABASE_URL", "")

_INSERT_SQL = """
    INSERT INTO documents
        (original_text, summary, keywords, trend_score,
         matched_trends, image_prompt, image_local_path, content_embedding)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
"""

_TABLE_DDL = """
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS documents (
        id                SERIAL PRIMARY KEY,
        original_text     TEXT        NOT NULL,
        summary           TEXT        NOT NULL,
        keywords          TEXT[]      NOT NULL DEFAULT '{}',
        trend_score       FLOAT       NOT NULL DEFAULT 0.0,
        matched_trends    TEXT[]      NOT NULL DEFAULT '{}',
        image_prompt      TEXT        NOT NULL DEFAULT '',
        image_local_path  TEXT        NOT NULL DEFAULT '',
        content_embedding vector(768),
        created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
"""


def _bootstrap() -> None:
    """Create assets directory and PostgreSQL table on server startup."""
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Assets directory ready: %s", _ASSETS_DIR.resolve())

    if not _DATABASE_URL:
        logger.warning("STORAGE_DATABASE_URL not set — pg_insert_document will fail at call time")
        return
    try:
        import psycopg2
        conn = psycopg2.connect(_DATABASE_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            for statement in _TABLE_DDL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    cur.execute(stmt)
        conn.close()
        logger.info("PostgreSQL documents table ready")
    except Exception as exc:
        logger.warning("PostgreSQL bootstrap warning (table may already exist): %s", exc)


# ---------------------------------------------------------------------------
# Tool: save_asset_locally
# ---------------------------------------------------------------------------


def _tool_save_asset_locally(arguments: dict[str, Any]) -> dict[str, Any]:
    filename: str = arguments["filename"]
    binary_data: str = arguments["binary_data"]

    # Sanitise filename — strip directory components to prevent path traversal
    safe_name = Path(filename).name
    dest = _ASSETS_DIR / safe_name

    try:
        raw_bytes = base64.b64decode(binary_data)
    except Exception as exc:
        return _err(f"base64 decode failed: {exc}")

    dest.write_bytes(raw_bytes)
    relative = str(Path("assets") / "images" / safe_name)
    logger.info("Asset saved: %s (%d bytes)", relative, len(raw_bytes))
    return {"path": relative}


# ---------------------------------------------------------------------------
# Tool: generate_embedding
# ---------------------------------------------------------------------------


def _tool_generate_embedding(arguments: dict[str, Any]) -> dict[str, Any]:
    text: str = arguments["text"]
    if not text.strip():
        return _err("text is empty — cannot generate embedding")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _err("GEMINI_API_KEY is not set")

    try:
        from google import genai
        from google.genai import types as gtypes

        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model="models/text-embedding-004",
            contents=text,
            config=gtypes.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        embeddings = response.embeddings or []
        vector: list[float] = list(embeddings[0].values or [])
        logger.info("Embedding generated: %d dims", len(vector))
        return {"embedding": vector}
    except Exception as exc:
        return _err(f"Gemini embedding failed: {exc}")


# ---------------------------------------------------------------------------
# Tool: pg_insert_document
# ---------------------------------------------------------------------------


def _tool_pg_insert_document(arguments: dict[str, Any]) -> dict[str, Any]:
    if not _DATABASE_URL:
        return _err("STORAGE_DATABASE_URL is not configured")

    required = {"original_text", "summary", "content_embedding"}
    missing = required - arguments.keys()
    if missing:
        return _err(f"Missing required fields: {sorted(missing)}")

    embedding: list[float] = arguments["content_embedding"]
    if not embedding:
        return _err("content_embedding is empty — refusing to insert")

    try:
        import psycopg2
        from pgvector.psycopg2 import register_vector
        import numpy as np

        conn = psycopg2.connect(_DATABASE_URL)
        register_vector(conn)

        row = (
            arguments["original_text"],
            arguments["summary"],
            arguments.get("keywords", []),
            float(arguments.get("trend_score", 0.0)),
            arguments.get("matched_trends", []),
            arguments.get("image_prompt", ""),
            arguments.get("image_local_path", ""),
            np.array(embedding, dtype=np.float32),
        )

        with conn.cursor() as cur:
            cur.execute(_INSERT_SQL, row)
            document_id: int = cur.fetchone()[0]  # type: ignore[index]
        conn.commit()
        conn.close()

        logger.info("Document inserted: id=%d", document_id)
        return {"document_id": document_id, "status": "inserted"}
    except Exception as exc:
        return _err(f"PostgreSQL insert failed: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _err(message: str) -> dict[str, Any]:
    logger.error(message)
    return {"error": message}


# ---------------------------------------------------------------------------
# JSON-RPC dispatch
# ---------------------------------------------------------------------------

_TOOL_HANDLERS = {
    "save_asset_locally": _tool_save_asset_locally,
    "generate_embedding":  _tool_generate_embedding,
    "pg_insert_document":  _tool_pg_insert_document,
}


def _handle_tools_list(request_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS_MANIFEST}}


def _handle_tools_call(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name: str = params.get("name", "")
    arguments: dict[str, Any] = params.get("arguments", {})
    handler = _TOOL_HANDLERS.get(name)

    if handler is None:
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    result = handler(arguments)

    if "error" in result:
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32603, "message": result["error"]}}

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    method: str = request.get("method", "")
    params: dict[str, Any] = request.get("params", {})

    if method == "tools/list":
        return _handle_tools_list(request_id)
    if method == "tools/call":
        return _handle_tools_call(request_id, params)

    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(levelname)s  storage_server  %(message)s")
    _bootstrap()
    logger.info("Storage MCP server ready — listening on stdin")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": str(exc)}}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
