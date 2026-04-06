"""
Lightweight MCP subprocess transport — standalone, no imports from the main backend.

Spawns an MCP server as a child process on context-manager entry, communicates
via stdin/stdout JSON-RPC 2.0, terminates on exit.

Usage:
    with MCPClient("uv run mcp-storage-server") as mcp:
        result = mcp.call("pg_insert_document", {...})
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
import time
from typing import Any

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Raised when an MCP tool call returns an error response or the subprocess fails."""


class MCPClient:
    """
    Manages a single MCP server subprocess and exchanges JSON-RPC 2.0 messages
    over its stdin / stdout streams.

    Args:
        command: Shell-style command string for the MCP server process.
                 Will be split with shlex.split.
        env:     Optional environment variable overrides for the subprocess.
                 If None, the current process environment is inherited.
    """

    def __init__(self, command: str, env: dict[str, str] | None = None) -> None:
        self._command: list[str] = shlex.split(command)
        self._env = env
        self._proc: subprocess.Popen[str] | None = None
        self._req_id: int = 0

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Spawn the MCP server subprocess."""
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._env,
        )
        logger.info(
            "MCPClient started: %s (pid=%d)",
            self._command[0],
            self._proc.pid,
        )

    def stop(self) -> None:
        """Gracefully terminate (then kill if necessary) the MCP server subprocess."""
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
            logger.info("MCPClient stopped: %s", self._command[0])
        except subprocess.TimeoutExpired:
            logger.warning(
                "MCPClient %s did not exit in 5 s — killing.",
                self._command[0],
            )
            self._proc.kill()
            self._proc.wait()
        finally:
            self._proc = None

    # ── RPC ──────────────────────────────────────────────────────────────────

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Send a tools/call JSON-RPC 2.0 request and return the result dict.

        Wire format (newline-delimited JSON):
            Request:  {"jsonrpc": "2.0", "id": N, "method": "tools/call",
                       "params": {"name": <tool_name>, "arguments": <arguments>}}
            Response: {"jsonrpc": "2.0", "id": N, "result": {...}}
                   or {"jsonrpc": "2.0", "id": N, "error": {"message": "..."}}

        Raises:
            MCPError: if the server is not started, stdout closes unexpectedly,
                      or the response contains an "error" key.
        """
        if self._proc is None:
            raise MCPError("MCPClient.call() called before start()")

        self._req_id += 1
        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        line = json.dumps(request) + "\n"

        assert self._proc.stdin is not None, "stdin pipe unexpectedly None"
        assert self._proc.stdout is not None, "stdout pipe unexpectedly None"

        t0 = time.monotonic()
        self._proc.stdin.write(line)
        self._proc.stdin.flush()

        raw = self._proc.stdout.readline()
        duration_ms = (time.monotonic() - t0) * 1000

        if not raw:
            raise MCPError(
                f"MCP server '{self._command[0]}' closed stdout unexpectedly "
                f"during call to '{tool_name}'"
            )

        response: dict[str, Any] = json.loads(raw)

        if "error" in response:
            error_msg: str = response["error"].get("message", str(response["error"]))
            raise MCPError(f"MCP tool error ({tool_name}): {error_msg}")

        logger.debug(
            "MCPClient.call(%s) completed in %.1f ms",
            tool_name,
            duration_ms,
        )
        result: dict[str, Any] = response["result"]
        return result

    # ── Context manager ──────────────────────────────────────────────────────

    def __enter__(self) -> MCPClient:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
