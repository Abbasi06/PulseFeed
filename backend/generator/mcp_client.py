from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Raised when an MCP tool call returns an error or the subprocess fails."""


class MCPClient:
    """Manages a single MCP server subprocess and sends/receives JSON-RPC calls."""

    def __init__(self, command: list[str], env: dict[str, str] | None = None) -> None:
        self._command = command
        self._env = env
        self._proc: subprocess.Popen[str] | None = None
        self._request_id = 0

    def start(self) -> None:
        """Launch the MCP server subprocess."""
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            env=self._env,
        )
        logger.info("MCP server started: %s (pid=%d)", self._command[0], self._proc.pid)

    def stop(self) -> None:
        """Terminate the MCP server subprocess."""
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send a tools/call request and return the result dict."""
        if self._proc is None:
            raise MCPError("MCP server not started")
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        line = json.dumps(request) + "\n"
        t0 = time.monotonic()
        assert self._proc.stdin is not None
        self._proc.stdin.write(line)
        self._proc.stdin.flush()
        assert self._proc.stdout is not None
        raw = self._proc.stdout.readline()
        duration_ms = (time.monotonic() - t0) * 1000
        if not raw:
            raise MCPError(f"MCP server {self._command[0]} closed stdout unexpectedly")
        response = json.loads(raw)
        if "error" in response:
            raise MCPError(f"MCP tool error ({tool_name}): {response['error']['message']}")
        logger.debug("MCP call %s in %.1fms", tool_name, duration_ms)
        return response["result"]  # type: ignore[return-value]

    def __enter__(self) -> MCPClient:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
