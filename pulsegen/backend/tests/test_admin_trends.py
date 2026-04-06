"""
Tests for trends admin routes:
  GET /admin/trends/keywords
  GET /admin/trends/runs

Uses a real temp SQLite database (tmp_db fixture) via GENERATOR_DB_PATH env.
"""

import os
import sqlite3
from unittest.mock import patch

from fastapi.testclient import TestClient

from admin_api.main import app

client = TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS trend_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,
    category TEXT NOT NULL,
    context TEXT NOT NULL DEFAULT '',
    source_count INTEGER NOT NULL DEFAULT 1,
    run_id TEXT NOT NULL,
    collected_at TEXT NOT NULL
)
"""


def _seed_keywords(db_path: str, rows: list[tuple]) -> None:
    """Insert rows: (term, category, context, source_count, run_id, collected_at)."""
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_TABLE)
    conn.executemany(
        "INSERT INTO trend_keywords (term, category, context, source_count, run_id, collected_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


class TestGetTrendKeywords:
    def test_returns_200(self, tmp_db: str) -> None:
        _seed_keywords(tmp_db, [
            ("Flash Attention", "AI Engineering", "performance", 3, "run-1", "2024-01-15T12:00:00"),
        ])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/keywords")
        assert resp.status_code == 200

    def test_returns_list(self, tmp_db: str) -> None:
        _seed_keywords(tmp_db, [("vLLM", "AI Engineering", "serving", 2, "run-1", "2024-01-15T12:00:00")])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/keywords")
        assert isinstance(resp.json(), list)

    def test_keyword_fields_present(self, tmp_db: str) -> None:
        _seed_keywords(tmp_db, [("Mamba SSM", "AI Engineering", "architecture", 4, "run-1", "2024-01-15T12:00:00")])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/keywords")
        kw = resp.json()[0]
        assert kw["term"] == "Mamba SSM"
        assert kw["category"] == "AI Engineering"
        assert kw["source_count"] == 4

    def test_multiple_keywords_returned(self, tmp_db: str) -> None:
        rows = [
            ("Flash Attention", "AI Engineering", "ctx", 3, "run-1", "2024-01-15T12:00:02"),
            ("vLLM", "MLOps", "ctx", 2, "run-1", "2024-01-15T12:00:01"),
            ("CUDA Graph", "GPU Optimization", "ctx", 5, "run-1", "2024-01-15T12:00:00"),
        ]
        _seed_keywords(tmp_db, rows)
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/keywords")
        assert len(resp.json()) == 3

    def test_limit_param_reduces_results(self, tmp_db: str) -> None:
        rows = [(f"Term{i}", "AI Engineering", "ctx", i, "run-1", f"2024-01-15T12:00:{i:02d}") for i in range(10)]
        _seed_keywords(tmp_db, rows)
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/keywords?limit=3")
        assert len(resp.json()) <= 3

    def test_empty_table_returns_empty_list(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.execute(_CREATE_TABLE)
        conn.commit()
        conn.close()
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/keywords")
        assert resp.json() == []

    def test_db_unavailable_returns_empty_list(self) -> None:
        with patch("admin_api.routes.trends._get_db_connection", return_value=None):
            resp = client.get("/admin/trends/keywords")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetTrendRuns:
    def test_returns_200(self, tmp_db: str) -> None:
        _seed_keywords(tmp_db, [("Flash Attention", "AI", "ctx", 3, "run-abc", "2024-01-15T12:00:00")])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/runs")
        assert resp.status_code == 200

    def test_run_fields_present(self, tmp_db: str) -> None:
        _seed_keywords(tmp_db, [("Term", "Cat", "ctx", 2, "run-xyz", "2024-01-15T10:00:00")])
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/runs")
        run = resp.json()[0]
        assert run["run_id"] == "run-xyz"
        assert run["collected_at"] == "2024-01-15T10:00:00"

    def test_distinct_runs_returned(self, tmp_db: str) -> None:
        # Use the same (run_id, collected_at, source_count) values per run to
        # avoid the SQL DISTINCT (run_id, collected_at, source_count) returning
        # multiple rows for the same run_id when source_count differs.
        rows = [
            ("Term1", "AI", "ctx", 3, "run-1", "2024-01-15T12:00:00"),
            ("Term2", "AI", "ctx", 3, "run-1", "2024-01-15T12:00:00"),  # same source_count
            ("Term3", "AI", "ctx", 1, "run-2", "2024-01-14T12:00:00"),
        ]
        _seed_keywords(tmp_db, rows)
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/runs")
        run_ids = [r["run_id"] for r in resp.json()]
        assert len(run_ids) == len(set(run_ids))  # distinct

    def test_empty_table_returns_empty_list(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.execute(_CREATE_TABLE)
        conn.commit()
        conn.close()
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": tmp_db}):
            resp = client.get("/admin/trends/runs")
        assert resp.json() == []

    def test_db_unavailable_returns_empty_list(self) -> None:
        with patch("admin_api.routes.trends._get_db_connection", return_value=None):
            resp = client.get("/admin/trends/runs")
        assert resp.status_code == 200
        assert resp.json() == []
