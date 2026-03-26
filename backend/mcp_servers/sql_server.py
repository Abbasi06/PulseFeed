from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
from typing import Any

logger = logging.getLogger(__name__)

TOOLS_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "query",
        "description": "Execute a SELECT statement and return rows.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
                "params": {"type": ["array", "null"]},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "execute",
        "description": "Execute an INSERT, UPDATE, DELETE, or DDL statement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
                "params": {"type": ["array", "null"]},
            },
            "required": ["sql"],
        },
    },
]

_FORBIDDEN_PATTERNS: list[str] = ["DROP TABLE", "DROP DATABASE", "ATTACH DATABASE"]


def _open_connection() -> sqlite3.Connection:
    db_path = os.environ.get("DATABASE_PATH", "./generator.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


_conn: sqlite3.Connection = _open_connection()


def _tool_query(arguments: dict[str, Any]) -> dict[str, Any] | dict[str, Any]:
    sql: str = arguments["sql"]
    params: list[Any] = arguments.get("params") or []

    if not sql.strip().upper().startswith("SELECT"):
        return {"error": {"code": -32600, "message": "query tool only accepts SELECT statements"}}

    cursor = _conn.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    return {"rows": rows, "row_count": len(rows)}


def _tool_execute(arguments: dict[str, Any]) -> dict[str, Any]:
    sql: str = arguments["sql"]
    params: list[Any] = arguments.get("params") or []
    sql_upper = sql.upper()

    for pattern in _FORBIDDEN_PATTERNS:
        if pattern in sql_upper:
            return {"error": {"code": -32600, "message": f"Forbidden SQL pattern: {pattern}"}}

    cursor = _conn.execute(sql, params)
    _conn.commit()
    return {"rows_affected": cursor.rowcount, "last_insert_id": cursor.lastrowid}


def _handle_tools_list(request_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS_MANIFEST}}


def _handle_tools_call(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name: str = params.get("name", "")
    arguments: dict[str, Any] = params.get("arguments", {})

    if name == "query":
        result = _tool_query(arguments)
    elif name == "execute":
        result = _tool_execute(arguments)
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown tool: {name}"},
        }

    if "error" in result:
        return {"jsonrpc": "2.0", "id": request_id, "error": result["error"]}

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


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logger.info("sql server started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
