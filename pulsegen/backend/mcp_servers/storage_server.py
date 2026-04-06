"""
Storage MCP Server
------------------
Exposes three tools to the Storage Orchestrator Agent over stdio JSON-RPC 2.0:

  save_asset_locally   — writes a base64-encoded image to ./assets/images/
  generate_embedding   — calls Ollama nomic-embed-text (768 dims)
  pg_insert_document   — inserts a fully-processed document into PostgreSQL
                         with a pgvector content_embedding column

Environment variables (all read at startup):
  OLLAMA_BASE_URL       Ollama base URL (default: http://ollama:11434/v1)
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
        "description": "Embed text with Ollama nomic-embed-text (768 dims) and return a float array.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text":  {"type": "string"},
                "model": {"type": "string", "description": "Embedding model ID (default: nomic-embed-text)"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "pg_insert_document",
        "description": "Insert a fully processed document into the generator_documents PostgreSQL table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source":                 {"type": "string"},
                "source_id":              {"type": "string"},
                "url":                    {"type": "string"},
                "url_hash":               {"type": "string"},
                "content_hash":           {"type": "string"},
                "title":                  {"type": "string"},
                "author":                 {"type": "string"},
                "published_at":           {"type": "string"},
                "summary":                {"type": "string"},
                "bm25_keywords":          {"type": "array", "items": {"type": "string"}},
                "taxonomy_tags":          {"type": "array", "items": {"type": "string"}},
                "image_url":              {"type": "string"},
                "gatekeeper_confidence":  {"type": "number"},
                "embedding":              {"type": "array", "items": {"type": "number"}},
                "pipeline_status":        {"type": "string"},
                "processed_at":           {"type": "string"},
            },
            "required": ["source", "url", "url_hash", "content_hash", "title", "summary", "embedding"],
        },
    },
]

# ---------------------------------------------------------------------------
# Startup: assets directory + PostgreSQL table
# ---------------------------------------------------------------------------

_ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", "./assets/images"))
_DATABASE_URL = os.environ.get("STORAGE_DATABASE_URL", "")

_INSERT_SQL = """
    INSERT INTO generator_documents
        (source, source_id, url, url_hash, content_hash, title, author,
         published_at, summary, bm25_keywords, taxonomy_tags, image_url,
         gatekeeper_confidence, pipeline_status, processed_at, embedding)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (url_hash) DO NOTHING
    RETURNING id
"""

_TABLE_DDL = """
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS generator_documents (
        id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        source                TEXT        NOT NULL,
        source_id             TEXT,
        url                   TEXT        NOT NULL,
        url_hash              TEXT        NOT NULL UNIQUE,
        content_hash          TEXT        NOT NULL,
        title                 TEXT        NOT NULL,
        author                TEXT,
        published_at          TIMESTAMPTZ,
        summary               TEXT        NOT NULL DEFAULT '',
        bm25_keywords         TEXT[]      NOT NULL DEFAULT '{}',
        taxonomy_tags         TEXT        NOT NULL DEFAULT '[]',
        image_url             TEXT        NOT NULL DEFAULT '',
        gatekeeper_confidence FLOAT       NOT NULL DEFAULT 0.0,
        pipeline_status       TEXT        NOT NULL DEFAULT 'stored',
        processed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        embedding             vector(768)
    );
    CREATE INDEX IF NOT EXISTS idx_gendocs_source ON generator_documents(source);
    CREATE INDEX IF NOT EXISTS idx_gendocs_processed_at ON generator_documents(processed_at DESC);
    CREATE INDEX IF NOT EXISTS idx_gendocs_url_hash ON generator_documents(url_hash);
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
        conn = psycopg2.connect(_DATABASE_URL, connect_timeout=5)
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

    model: str = arguments.get("model") or "nomic-embed-text"
    embed_url = os.environ.get("LLM_EMBED_URL", "http://host.docker.internal:8082/v1")
    api_key = os.environ.get("LLM_API_KEY", "local")

    try:
        from openai import OpenAI

        client = OpenAI(base_url=embed_url, api_key=api_key)
        response = client.embeddings.create(model=model, input=text)
        vector: list[float] = response.data[0].embedding
        logger.info("Embedding generated: %d dims via %s", len(vector), model)
        return {"embedding": vector}
    except Exception as exc:
        return _err(f"Ollama embedding failed: {exc}")


# ---------------------------------------------------------------------------
# Tool: pg_insert_document
# ---------------------------------------------------------------------------


def _tool_pg_insert_document(arguments: dict[str, Any]) -> dict[str, Any]:
    if not _DATABASE_URL:
        return _err("STORAGE_DATABASE_URL is not configured")

    required = {"source", "url", "url_hash", "content_hash", "title", "summary", "embedding"}
    missing = required - arguments.keys()
    if missing:
        return _err(f"Missing required fields: {sorted(missing)}")

    embedding: list[float] = arguments["embedding"]
    if not embedding:
        return _err("embedding is empty — refusing to insert")

    try:
        import json as _json

        import numpy as np
        import psycopg2
        from pgvector.psycopg2 import register_vector

        conn = psycopg2.connect(_DATABASE_URL, connect_timeout=5)
        register_vector(conn)

        published_at = arguments.get("published_at")
        taxonomy_tags = arguments.get("taxonomy_tags", [])
        taxonomy_json = _json.dumps(taxonomy_tags) if isinstance(taxonomy_tags, list) else taxonomy_tags

        row = (
            arguments["source"],
            arguments.get("source_id"),
            arguments["url"],
            arguments["url_hash"],
            arguments["content_hash"],
            arguments["title"],
            arguments.get("author"),
            published_at or None,
            arguments["summary"],
            arguments.get("bm25_keywords", []),
            taxonomy_json,
            arguments.get("image_url") or "",
            float(arguments.get("gatekeeper_confidence", 0.0)),
            arguments.get("pipeline_status", "stored"),
            arguments.get("processed_at"),
            np.array(embedding, dtype=np.float32),
        )

        with conn.cursor() as cur:
            cur.execute(_INSERT_SQL, row)
            result_row = cur.fetchone()
        conn.commit()
        conn.close()

        if result_row is None:
            # ON CONFLICT DO NOTHING — document already existed
            logger.info("Document skipped (duplicate url_hash): %s", arguments["url_hash"])
            return {"document_id": arguments["url_hash"], "status": "duplicate"}

        document_id: str = str(result_row[0])
        logger.info("Document inserted: id=%s", document_id)
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
