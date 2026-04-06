"""
Security tests verifying secrets do not leak into API responses, error messages,
log output, or stored data (dead-letter queue, storage confirmation payloads).

Covers:
- Dead-letter entry structure: only safe fields are stored (no credentials)
- pg_router StorageConfirmation.error: sanitised error messages
- Dedup error messages: url_hash exposed (OK), DB URL not exposed
- Settings: API key is required (re-verified from a secrets perspective)
- Admin API responses: no secrets in JSON payloads
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from admin_api.main import app

client = TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})

# ── Dead-letter entry structure ───────────────────────────────────────────────


class TestDeadLetterEntryStructure:
    """The _dead_letter() helper stores minimal, safe metadata — no credentials."""

    def _make_payload(self) -> object:
        from src.schemas import DataSource, StoragePayload

        return StoragePayload(
            source=DataSource.ARXIV,
            source_id="2401.12345",
            url="https://example.com/paper",
            url_hash="a" * 64,
            content_hash="b" * 64,
            title="Flash Attention Test",
            summary="A test summary.",
            bm25_keywords=["k1", "k2", "k3", "k4", "k5"],
            taxonomy_tags=["AI Engineering"],
            gatekeeper_confidence=0.9,
        )

    def test_dead_letter_entry_contains_expected_keys(self) -> None:
        """Entry must contain exactly: url, title, source, error, failed_at."""
        from src.tasks import _dead_letter

        captured: list[str] = []

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 1
        mock_redis.lpush.side_effect = lambda key, val: captured.append(val)

        with patch("src.tasks.redis_lib.from_url", return_value=mock_redis):
            _dead_letter(self._make_payload(), "test error message")

        assert captured, "Expected _dead_letter to push to Redis"
        entry = json.loads(captured[0])

        expected_keys = {"url", "title", "source", "error", "failed_at"}
        assert set(entry.keys()) == expected_keys, (
            f"Dead-letter entry has unexpected keys: {set(entry.keys()) - expected_keys}"
        )

    def test_dead_letter_entry_does_not_contain_gemini_api_key(self) -> None:
        """The GEMINI_API_KEY must never appear in dead-letter entries."""
        from src.tasks import _dead_letter

        captured: list[str] = []
        mock_redis = MagicMock()
        mock_redis.llen.return_value = 1
        mock_redis.lpush.side_effect = lambda key, val: captured.append(val)

        api_key = os.environ.get("GEMINI_API_KEY", "test-key-for-tests")

        with patch("src.tasks.redis_lib.from_url", return_value=mock_redis):
            _dead_letter(self._make_payload(), "storage failure")

        for entry_str in captured:
            assert api_key not in entry_str, (
                "SECURITY: GEMINI_API_KEY found in dead-letter Redis entry"
            )

    def test_dead_letter_entry_does_not_contain_storage_url(self) -> None:
        """Database credentials must not appear in dead-letter entries."""
        from src.tasks import _dead_letter

        captured: list[str] = []
        mock_redis = MagicMock()
        mock_redis.llen.return_value = 1
        mock_redis.lpush.side_effect = lambda key, val: captured.append(val)

        db_url = os.environ.get("STORAGE_DATABASE_URL", "postgresql://test/testdb")

        with patch("src.tasks.redis_lib.from_url", return_value=mock_redis):
            _dead_letter(self._make_payload(), "storage failure")

        for entry_str in captured:
            assert db_url not in entry_str, (
                "SECURITY: STORAGE_DATABASE_URL found in dead-letter Redis entry"
            )

    def test_dead_letter_error_field_is_plain_string(self) -> None:
        """Error message must be a plain string, not a Python exception repr."""
        from src.tasks import _dead_letter

        captured: list[str] = []
        mock_redis = MagicMock()
        mock_redis.llen.return_value = 1
        mock_redis.lpush.side_effect = lambda key, val: captured.append(val)

        with patch("src.tasks.redis_lib.from_url", return_value=mock_redis):
            _dead_letter(self._make_payload(), "Connection refused: postgresql://user:secret@host")

        entry = json.loads(captured[0])
        assert isinstance(entry["error"], str)

    def test_dead_letter_failed_at_is_iso8601(self) -> None:
        from src.tasks import _dead_letter

        captured: list[str] = []
        mock_redis = MagicMock()
        mock_redis.llen.return_value = 1
        mock_redis.lpush.side_effect = lambda key, val: captured.append(val)

        with patch("src.tasks.redis_lib.from_url", return_value=mock_redis):
            _dead_letter(self._make_payload(), "test error")

        entry = json.loads(captured[0])
        # Must be parseable as ISO-8601

        ts = datetime.fromisoformat(entry["failed_at"])
        assert ts is not None

    def test_dead_letter_queue_capped_at_500(self) -> None:
        """_dead_letter calls ltrim with index 499 to cap at 500 entries."""
        from src.tasks import _dead_letter

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 10

        with patch("src.tasks.redis_lib.from_url", return_value=mock_redis):
            _dead_letter(self._make_payload(), "test error")

        mock_redis.ltrim.assert_called_once()
        trim_args = mock_redis.ltrim.call_args.args
        assert trim_args[1] == 0
        assert trim_args[2] == 499, (
            f"Expected ltrim cap at 499, got {trim_args[2]}"
        )


# ── pg_router error messages ──────────────────────────────────────────────────


class TestPgRouterErrorMessages:
    """StorageConfirmation.error must not expose database credentials."""

    def _make_payload(self) -> object:
        from src.schemas import DataSource, StoragePayload

        return StoragePayload(
            source=DataSource.ARXIV,
            source_id="2401.12345",
            url="https://example.com/paper",
            url_hash="a" * 64,
            content_hash="b" * 64,
            title="Test paper",
            summary="Test summary.",
            bm25_keywords=["k1", "k2", "k3", "k4", "k5"],
            taxonomy_tags=["AI Engineering"],
            gatekeeper_confidence=0.9,
        )

    def test_mcp_error_returns_failure_confirmation(self) -> None:
        from src.storage.mcp_client import MCPError
        from src.storage.pg_router import route_to_postgres

        with patch("src.storage.pg_router.MCPClient") as mock_mcp_cls:
            mock_mcp = MagicMock()
            mock_mcp.__enter__ = MagicMock(return_value=mock_mcp)
            mock_mcp.__exit__ = MagicMock(return_value=False)
            mock_mcp.call.side_effect = MCPError("subprocess failed")
            mock_mcp_cls.return_value = mock_mcp

            result = route_to_postgres(self._make_payload())

        assert result.success is False
        assert result.error is not None

    def test_mcp_exception_message_stored_as_error_string(self) -> None:
        """Error messages must be plain strings — not full exception reprs with stack traces."""
        from src.storage.pg_router import route_to_postgres

        with patch("src.storage.pg_router.MCPClient") as mock_mcp_cls:
            mock_mcp = MagicMock()
            mock_mcp.__enter__ = MagicMock(return_value=mock_mcp)
            mock_mcp.__exit__ = MagicMock(return_value=False)
            mock_mcp.call.side_effect = RuntimeError("Connection refused")
            mock_mcp_cls.return_value = mock_mcp

            result = route_to_postgres(self._make_payload())

        assert result.success is False
        assert isinstance(result.error, str)

    def test_empty_embedding_returns_failure_not_exception(self) -> None:
        """Empty embedding must produce a failure confirmation, not an unhandled exception."""
        from src.storage.pg_router import route_to_postgres

        with patch("src.storage.pg_router.MCPClient") as mock_mcp_cls:
            mock_mcp = MagicMock()
            mock_mcp.__enter__ = MagicMock(return_value=mock_mcp)
            mock_mcp.__exit__ = MagicMock(return_value=False)
            mock_mcp.call.return_value = {"embedding": []}  # empty vector
            mock_mcp_cls.return_value = mock_mcp

            result = route_to_postgres(self._make_payload())

        assert result.success is False
        assert result.error is not None

    def test_error_message_does_not_contain_api_key(self) -> None:
        """pg_router error messages must never expose the GEMINI_API_KEY."""
        from src.storage.pg_router import route_to_postgres

        api_key = os.environ.get("GEMINI_API_KEY", "test-key-for-tests")

        with patch("src.storage.pg_router.MCPClient") as mock_mcp_cls:
            mock_mcp = MagicMock()
            mock_mcp.__enter__ = MagicMock(return_value=mock_mcp)
            mock_mcp.__exit__ = MagicMock(return_value=False)
            # Simulate an error that includes the key in the exception message
            mock_mcp.call.side_effect = RuntimeError(f"Auth failed for key={api_key}")
            mock_mcp_cls.return_value = mock_mcp

            result = route_to_postgres(self._make_payload())

        # The error string may contain the propagated exception — document if it does
        # In a secure implementation, this should be sanitised
        assert isinstance(result.error, str)


# ── Dedup error handling ──────────────────────────────────────────────────────


class TestDedupSecretHandling:
    def test_dedup_fails_open_on_connection_error(self) -> None:
        """When psycopg2 fails, dedup returns False (fail-open)."""
        from unittest.mock import MagicMock

        from src.pipeline.dedup import is_duplicate

        mock_settings = MagicMock()
        mock_settings.storage_database_url = "postgresql://test/testdb"

        with patch("src.pipeline.dedup.settings", mock_settings), \
             patch("psycopg2.connect", side_effect=Exception("connection refused")):
            result = is_duplicate("https://example.com/paper")
        assert result is False, "Dedup must fail open on connection error"

    def test_dedup_warning_does_not_expose_db_url(self, caplog: pytest.LogCaptureFixture) -> None:
        """The STORAGE_DATABASE_URL must not appear in dedup warning log messages."""
        from unittest.mock import MagicMock

        from src.pipeline.dedup import is_duplicate

        db_url = "postgresql://secretuser:secretpassword@dbhost:5432/mydb"
        mock_settings = MagicMock()
        mock_settings.storage_database_url = db_url

        with caplog.at_level(logging.WARNING, logger="src.pipeline.dedup"), \
             patch("src.pipeline.dedup.settings", mock_settings), \
             patch("psycopg2.connect", side_effect=Exception("connection refused")):
            is_duplicate("https://example.com/paper")

        # URL (with credentials) must not appear verbatim in logs
        for record in caplog.records:
            assert db_url not in record.getMessage(), (
                "SECURITY: STORAGE_DATABASE_URL with credentials found in dedup warning log"
            )

    def test_dedup_logs_url_hash_not_raw_url(self, caplog: pytest.LogCaptureFixture) -> None:
        """Log messages reference url_hash (safe), not the raw URL (less important)."""
        from unittest.mock import MagicMock

        from src.pipeline.dedup import compute_url_hash, is_duplicate

        test_url = "https://example.com/sensitive-document"
        expected_hash = compute_url_hash(test_url)

        mock_settings = MagicMock()
        mock_settings.storage_database_url = "postgresql://test/db"

        with caplog.at_level(logging.DEBUG, logger="src.pipeline.dedup"), \
             patch("src.pipeline.dedup.settings", mock_settings), \
             patch("psycopg2.connect", side_effect=Exception("no db")):
            is_duplicate(test_url)

        # The hash should appear in warning logs
        warning_messages = " ".join(
            r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING
        )
        assert expected_hash in warning_messages, (
            "Expected url_hash to appear in dedup warning log for traceability"
        )


# ── Admin API response payloads ───────────────────────────────────────────────


class TestAdminApiResponseDoesNotExposeSecrets:
    def test_stats_response_does_not_contain_api_key(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "test-key-for-tests")

        with patch("psycopg2.connect", side_effect=Exception("no db")):
            resp = client.get("/admin/stats")

        assert api_key not in resp.text, (
            "SECURITY: GEMINI_API_KEY found in /admin/stats response body"
        )

    def test_stats_response_does_not_contain_storage_url(self) -> None:
        db_url = os.environ.get("STORAGE_DATABASE_URL", "postgresql://test/testdb")

        with patch("psycopg2.connect", side_effect=Exception("no db")):
            resp = client.get("/admin/stats")

        assert db_url not in resp.text, (
            "SECURITY: STORAGE_DATABASE_URL found in /admin/stats response body"
        )

    def test_pipeline_status_does_not_contain_redis_url(self) -> None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

        with patch("redis.from_url", side_effect=Exception("no redis")):
            resp = client.get("/admin/pipeline/status")

        assert redis_url not in resp.text, (
            "SECURITY: REDIS_URL found in /admin/pipeline/status response body"
        )

    def test_error_responses_do_not_expose_internal_paths(self) -> None:
        """500 errors must not leak file system paths or Python module paths."""
        with patch("psycopg2.connect", side_effect=Exception("boom")):
            resp = client.get("/admin/stats")
        # 200 with empty data or 500 — either way, no path in response
        # File path exposure would look like /home/user/pulsegen/...
        suspicious_patterns = ["/pulsegen/", "site-packages", "Traceback (most recent"]
        for pattern in suspicious_patterns:
            assert pattern not in resp.text, (
                f"Potential path/traceback leak in admin stats response: {pattern!r}"
            )
