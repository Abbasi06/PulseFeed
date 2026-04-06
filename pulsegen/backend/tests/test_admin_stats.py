"""
Tests for GET /admin/stats — pipeline stats from PostgreSQL.
psycopg2.connect is mocked; no real database required.
"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from admin_api.main import app

client = TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})


def _make_conn(
    total: int = 42,
    by_source: list[tuple[str, int]] | None = None,
    taxonomy_rows: list[tuple[str]] | None = None,
    by_status: list[tuple[str, int]] | None = None,
    recent_rows: list[tuple] | None = None,
) -> MagicMock:
    """Return a mock psycopg2 connection with pre-set cursor return values."""
    if by_source is None:
        by_source = [("arxiv", 20), ("github", 15), ("devto", 7)]
    if taxonomy_rows is None:
        taxonomy_rows = [
            (json.dumps(["AI Engineering", "MLOps"]),),
            (json.dumps(["GPU Optimization"]),),
        ]
    if by_status is None:
        by_status = [("stored", 35), ("rejected", 7)]
    if recent_rows is None:
        recent_rows = [
            (1, "Test Doc", "arxiv", json.dumps(["AI Engineering"]), 0.9, datetime.now(UTC), "https://example.com"),
        ]

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (total,)
    mock_cursor.fetchall.side_effect = [by_source, taxonomy_rows, by_status, recent_rows]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


class TestGetStats:
    def test_returns_200_with_db_available_true(self) -> None:
        with patch("admin_api.routes.stats._get_connection", return_value=_make_conn()):
            resp = client.get("/admin/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["db_available"] is True

    def test_total_documents_correct(self) -> None:
        with patch("admin_api.routes.stats._get_connection", return_value=_make_conn(total=99)):
            resp = client.get("/admin/stats")
        assert resp.json()["total_documents"] == 99

    def test_by_source_populated(self) -> None:
        with patch("admin_api.routes.stats._get_connection", return_value=_make_conn()):
            resp = client.get("/admin/stats")
        by_source = resp.json()["by_source"]
        assert by_source["arxiv"] == 20
        assert by_source["github"] == 15

    def test_by_taxonomy_sorted_descending(self) -> None:
        taxonomy_rows = [
            (json.dumps(["AI Engineering"]),),
            (json.dumps(["AI Engineering", "MLOps"]),),
            (json.dumps(["MLOps"]),),
        ]
        with patch("admin_api.routes.stats._get_connection", return_value=_make_conn(taxonomy_rows=taxonomy_rows)):
            resp = client.get("/admin/stats")
        by_tax = resp.json()["by_taxonomy"]
        assert by_tax[0]["tag"] == "AI Engineering"  # count=2, highest
        counts = [item["count"] for item in by_tax]
        assert counts == sorted(counts, reverse=True)

    def test_by_status_populated(self) -> None:
        with patch("admin_api.routes.stats._get_connection", return_value=_make_conn()):
            resp = client.get("/admin/stats")
        assert "stored" in resp.json()["by_status"]

    def test_recent_documents_returned(self) -> None:
        with patch("admin_api.routes.stats._get_connection", return_value=_make_conn()):
            resp = client.get("/admin/stats")
        recent = resp.json()["recent_documents"]
        assert len(recent) >= 1
        assert "title" in recent[0]
        assert "confidence" in recent[0]

    def test_db_unavailable_returns_empty_response(self) -> None:
        with patch("admin_api.routes.stats._get_connection", return_value=None):
            resp = client.get("/admin/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["db_available"] is False
        assert data["total_documents"] == 0
        assert data["by_source"] == {}
        assert data["by_taxonomy"] == []

    def test_malformed_taxonomy_json_skipped(self) -> None:
        taxonomy_rows = [
            ("not-valid-json",),
            (json.dumps(["AI Engineering"]),),
        ]
        with patch("admin_api.routes.stats._get_connection", return_value=_make_conn(taxonomy_rows=taxonomy_rows)):
            resp = client.get("/admin/stats")
        # Should not raise; AI Engineering counted once
        assert resp.status_code == 200
        tags = {item["tag"]: item["count"] for item in resp.json()["by_taxonomy"]}
        assert tags.get("AI Engineering", 0) == 1
