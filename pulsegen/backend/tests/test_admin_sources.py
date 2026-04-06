"""
Tests for GET /admin/sources — per-connector quality records from SQLite.
Uses a real temp SQLite database (tmp_db fixture) via GENERATOR_DB_PATH env.
"""

import os
import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from admin_api.main import app

client = TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})


def _seed_sources(db_path: str, rows: list[tuple]) -> None:
    """Insert rows into source_quality table: (source_id, total_fetched, total_passed_gate, total_stored, last_updated)."""  # noqa: E501
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS source_quality (
            source_id TEXT PRIMARY KEY,
            total_fetched INTEGER DEFAULT 0,
            total_passed_gate INTEGER DEFAULT 0,
            total_stored INTEGER DEFAULT 0,
            last_updated TEXT
        )"""
    )
    conn.executemany(
        "INSERT INTO source_quality"
        " (source_id, total_fetched, total_passed_gate, total_stored, last_updated)"
        " VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


class TestGetSources:
    def test_returns_list(self, tmp_db: str) -> None:
        _seed_sources(tmp_db, [("arxiv", 100, 80, 75, "2024-01-15T12:00:00")])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/sources")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_source_record_fields_present(self, tmp_db: str) -> None:
        _seed_sources(tmp_db, [("github", 50, 40, 38, "2024-01-15T12:00:00")])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/sources")
        record = resp.json()[0]
        assert record["source_id"] == "github"
        assert record["total_fetched"] == 50
        assert record["total_passed_gate"] == 40
        assert record["total_stored"] == 38

    def test_pass_rate_calculated_correctly(self, tmp_db: str) -> None:
        _seed_sources(tmp_db, [("devto", 100, 75, 70, "2024-01-15T12:00:00")])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/sources")
        assert resp.json()[0]["pass_rate"] == pytest.approx(0.75)

    def test_zero_fetched_defaults_pass_rate_to_half(self, tmp_db: str) -> None:
        _seed_sources(tmp_db, [("rss", 0, 0, 0, None)])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/sources")
        assert resp.json()[0]["pass_rate"] == pytest.approx(0.5)

    def test_multiple_sources_returned(self, tmp_db: str) -> None:
        _seed_sources(tmp_db, [
            ("arxiv", 100, 80, 75, "2024-01-15"),
            ("github", 50, 40, 38, "2024-01-15"),
            ("devto", 30, 20, 18, "2024-01-15"),
        ])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/sources")
        assert len(resp.json()) == 3

    def test_sorted_by_total_fetched_descending(self, tmp_db: str) -> None:
        _seed_sources(tmp_db, [
            ("devto", 30, 20, 18, "2024-01-15"),
            ("arxiv", 100, 80, 75, "2024-01-15"),
            ("github", 50, 40, 38, "2024-01-15"),
        ])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/sources")
        fetched_values = [r["total_fetched"] for r in resp.json()]
        assert fetched_values == sorted(fetched_values, reverse=True)

    def test_empty_table_returns_empty_list(self, tmp_db: str) -> None:
        # Create table with no rows
        conn = sqlite3.connect(tmp_db)
        conn.execute(
            """CREATE TABLE source_quality (
                source_id TEXT PRIMARY KEY,
                total_fetched INTEGER DEFAULT 0,
                total_passed_gate INTEGER DEFAULT 0,
                total_stored INTEGER DEFAULT 0,
                last_updated TEXT
            )"""
        )
        conn.commit()
        conn.close()
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/sources")
        assert resp.json() == []

    def test_db_unavailable_returns_empty_list(self) -> None:
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": "/nonexistent/path/db.sqlite"}):
            with patch("admin_api.routes.sources._get_db_connection", return_value=None):
                resp = client.get("/admin/sources")
        assert resp.status_code == 200
        assert resp.json() == []
