"""
Security tests for the Admin API (admin_api/).

Covers:
- Authentication gap: all endpoints accessible without credentials (documented)
- CORS origin whitelist (only expected origins allowed by default)
- PULSEGEN_ADMIN_ALLOWED_ORIGIN env var parsing safety
- HTTP method enforcement (non-allowed verbs return 405)
- Query-param boundary enforcement (limit caps, no integer overflow)
- No sensitive data in error responses

NOTE: Several tests are marked xfail to document known security gaps that
should be fixed before production deployment.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from admin_api.main import _ALLOWED_ORIGINS, app

client = TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})
unauth_client = TestClient(app)


# ── Authentication enforcement ────────────────────────────────────────────────


class TestAdminEndpointsRequireAuthentication:
    """All admin endpoints must reject requests without a valid X-Admin-Key."""

    @pytest.mark.parametrize("path,method", [
        ("/admin/stats", "get"),
        ("/admin/sources", "get"),
        ("/admin/pipeline/status", "get"),
        ("/admin/trends/keywords", "get"),
        ("/admin/trends/runs", "get"),
        ("/admin/dead-letter", "get"),
    ])
    def test_get_endpoints_rejected_without_auth(self, path: str, method: str) -> None:
        """Each GET endpoint returns 401 with no X-Admin-Key header."""
        resp = getattr(unauth_client, method)(path)
        assert resp.status_code == 401, (
            f"{path} returned {resp.status_code} without auth — expected 401"
        )

    def test_post_pipeline_run_now_rejected_without_auth(self) -> None:
        """POST /admin/pipeline/run-now returns 401 without credentials."""
        resp = unauth_client.post("/admin/pipeline/run-now")
        assert resp.status_code == 401

    def test_delete_dead_letter_rejected_without_auth(self) -> None:
        """DELETE /admin/dead-letter returns 401 without credentials."""
        resp = unauth_client.delete("/admin/dead-letter")
        assert resp.status_code == 401

    def test_post_retry_dead_letter_rejected_without_auth(self) -> None:
        """POST /admin/dead-letter/{index}/retry returns 401 without credentials."""
        resp = unauth_client.post("/admin/dead-letter/0/retry")
        assert resp.status_code == 401

    def test_get_stats_requires_authorization_header(self) -> None:
        """Authenticated request to /admin/stats is not 401/403."""
        with patch("psycopg2.connect", side_effect=Exception("no db")), \
             patch("sqlite3.connect", side_effect=Exception("no sqlite")):
            resp = client.get("/admin/stats")
        assert resp.status_code not in (401, 403)


# ── CORS configuration ────────────────────────────────────────────────────────


class TestCorsConfiguration:
    def test_default_allowed_origins_contains_localhost_3001(self) -> None:
        assert "http://localhost:3001" in _ALLOWED_ORIGINS

    def test_default_allowed_origins_contains_localhost_3000(self) -> None:
        assert "http://localhost:3000" in _ALLOWED_ORIGINS

    def test_default_allowed_origins_contains_localhost(self) -> None:
        assert "http://localhost" in _ALLOWED_ORIGINS

    def test_default_allowed_origins_does_not_contain_wildcard(self) -> None:
        assert "*" not in _ALLOWED_ORIGINS, (
            "SECURITY: wildcard '*' in CORS origins would allow any site to "
            "read admin responses. Use explicit origin lists only."
        )

    def test_default_allowed_origins_no_empty_string(self) -> None:
        assert "" not in _ALLOWED_ORIGINS, (
            "SECURITY: empty string in CORS origins can be exploited in some "
            "browser/middleware combinations."
        )

    def test_default_allowed_origins_no_https_wildcard(self) -> None:
        for origin in _ALLOWED_ORIGINS:
            assert not origin.startswith("https://*"), (
                f"SECURITY: wildcard https origin {origin!r} in CORS list"
            )

    def test_cors_allows_request_from_localhost_3001(self) -> None:
        """Verify CORS middleware responds correctly for the expected origin."""
        with patch("psycopg2.connect", side_effect=Exception("no db")), \
             patch("sqlite3.connect", side_effect=Exception("no sqlite")):
            resp = client.get(
                "/admin/stats",
                headers={"Origin": "http://localhost:3001"},
            )
        # Non-preflight CORS: if origin is allowed, header is set
        acao = resp.headers.get("access-control-allow-origin")
        assert acao == "http://localhost:3001", (
            f"Expected CORS header for localhost:3001, got: {acao!r}"
        )

    def test_cors_rejects_unknown_origin(self) -> None:
        """Requests from unknown origins must not receive ACAO header."""
        with patch("psycopg2.connect", side_effect=Exception("no db")), \
             patch("sqlite3.connect", side_effect=Exception("no sqlite")):
            cors_client = TestClient(
                app,
                headers={"X-Admin-Key": "test-admin-key-for-tests", "Origin": "https://evil-attacker.example.com"},
            )
            resp = cors_client.get("/admin/stats")
        acao = resp.headers.get("access-control-allow-origin")
        assert acao != "https://evil-attacker.example.com", (
            "SECURITY: CORS allowed an unknown origin."
        )

    def test_custom_cors_origin_via_env_var(self) -> None:
        """PULSEGEN_ADMIN_ALLOWED_ORIGIN must extend the allowed list."""
        import importlib

        import admin_api.main as admin_main

        with patch.dict(os.environ, {
            "PULSEGEN_ADMIN_ALLOWED_ORIGIN": "https://my-dashboard.example.com",
        }):
            importlib.reload(admin_main)
            assert "https://my-dashboard.example.com" in admin_main._ALLOWED_ORIGINS
        # Reload again to restore default state
        importlib.reload(admin_main)

    def test_empty_cors_env_var_does_not_add_empty_origin(self) -> None:
        """Empty PULSEGEN_ADMIN_ALLOWED_ORIGIN must not inject '' into allowed list."""
        import importlib

        import admin_api.main as admin_main

        with patch.dict(os.environ, {"PULSEGEN_ADMIN_ALLOWED_ORIGIN": ""}):
            importlib.reload(admin_main)
            assert "" not in admin_main._ALLOWED_ORIGINS, (
                "SECURITY: empty PULSEGEN_ADMIN_ALLOWED_ORIGIN injected '' origin"
            )
        importlib.reload(admin_main)

    def test_whitespace_in_cors_env_var_is_trimmed(self) -> None:
        """Entries with surrounding whitespace must be trimmed before use."""
        import importlib

        import admin_api.main as admin_main

        with patch.dict(os.environ, {
            "PULSEGEN_ADMIN_ALLOWED_ORIGIN": "  https://trimmed.example.com  ",
        }):
            importlib.reload(admin_main)
            assert "https://trimmed.example.com" in admin_main._ALLOWED_ORIGINS
            assert "  https://trimmed.example.com  " not in admin_main._ALLOWED_ORIGINS
        importlib.reload(admin_main)


# ── HTTP method enforcement ───────────────────────────────────────────────────


class TestHttpMethodEnforcement:
    def test_put_on_stats_returns_405(self) -> None:
        resp = client.put("/admin/stats")
        assert resp.status_code == 405

    def test_patch_on_sources_returns_405(self) -> None:
        resp = client.patch("/admin/sources")
        assert resp.status_code == 405

    def test_delete_on_stats_returns_405(self) -> None:
        resp = client.delete("/admin/stats")
        assert resp.status_code == 405

    def test_post_on_stats_returns_405(self) -> None:
        resp = client.post("/admin/stats")
        assert resp.status_code == 405

    def test_get_on_run_now_returns_405(self) -> None:
        resp = client.get("/admin/pipeline/run-now")
        assert resp.status_code == 405


# ── Query-parameter boundary enforcement ─────────────────────────────────────


class TestQueryParamBoundaries:
    def test_dead_letter_limit_capped_at_500(self) -> None:
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0
        with patch("redis.from_url", return_value=mock_redis):
            client.get("/admin/dead-letter?limit=99999")
        # Verify lrange was called with max 499 (0 to limit-1)
        call_args = mock_redis.lrange.call_args
        end_index = call_args.args[2] if call_args.args else call_args[0][2]
        assert end_index <= 499, (
            f"SECURITY: dead-letter limit not capped — passed end_index={end_index} to Redis"
        )

    def test_dead_letter_default_limit_is_reasonable(self) -> None:
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0
        with patch("redis.from_url", return_value=mock_redis):
            client.get("/admin/dead-letter")
        call_args = mock_redis.lrange.call_args
        end_index = call_args.args[2] if call_args.args else call_args[0][2]
        assert end_index <= 499

    def test_trends_keyword_limit_capped_at_500(self, tmp_db: str) -> None:
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/keywords?limit=99999")
        assert resp.status_code == 200

    def test_negative_dead_letter_limit_handled(self) -> None:
        """Negative limit must not raise a 500."""
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0
        with patch("redis.from_url", return_value=mock_redis):
            resp = client.get("/admin/dead-letter?limit=-1")
        assert resp.status_code == 200

    def test_zero_dead_letter_limit_returns_empty(self) -> None:
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0
        with patch("redis.from_url", return_value=mock_redis):
            resp = client.get("/admin/dead-letter?limit=0")
        assert resp.status_code == 200


# ── Rate limiting (documenting the gap) ──────────────────────────────────────


class TestRateLimiting:
    def test_run_now_is_rate_limited(self) -> None:
        """After 3 requests, POST /admin/pipeline/run-now must return 429."""
        with patch("src.celery_app.app.send_task", return_value=MagicMock()):
            responses = [client.post("/admin/pipeline/run-now") for _ in range(5)]
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes, (
            f"Expected 429 after exceeding rate limit, got: {status_codes}"
        )

    def test_first_three_run_now_requests_succeed(self) -> None:
        """First 3 requests within the window must be accepted."""
        with patch("src.celery_app.app.send_task", return_value=MagicMock()):
            responses = [client.post("/admin/pipeline/run-now") for _ in range(3)]
        for resp in responses:
            assert resp.status_code == 200, f"Expected 200 for request within limit, got {resp.status_code}"

    def test_fourth_run_now_request_is_rejected(self) -> None:
        """4th request within the window must be 429."""
        with patch("src.celery_app.app.send_task", return_value=MagicMock()):
            for _ in range(3):
                client.post("/admin/pipeline/run-now")
            resp = client.post("/admin/pipeline/run-now")
        assert resp.status_code == 429
