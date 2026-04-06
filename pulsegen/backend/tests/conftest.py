"""
Shared fixtures for PulseGen backend tests.

All tests that touch SQLite use a fresh temp file per test.
All tests that touch Gemini/psycopg2/Redis use mocks — no real I/O.
GEMINI_API_KEY is injected into os.environ so Settings can be imported.
"""

import os
import sqlite3
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# ── Inject required env vars before any module-level Settings() instantiation ──
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-tests")
os.environ.setdefault("STORAGE_DATABASE_URL", "postgresql://test/testdb")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-for-tests")


# ── Temp SQLite fixture ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_run_now_rate_limiter() -> Generator[None]:
    """Clear the in-process rate-limiter state between tests."""
    from admin_api.routes.pipeline import _request_timestamps

    _request_timestamps.clear()
    yield
    _request_timestamps.clear()


@pytest.fixture()
def admin_client() -> TestClient:
    """TestClient with X-Admin-Key header pre-set for admin API tests."""
    from admin_api.main import app

    return TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})


@pytest.fixture()
def tmp_db(tmp_path: pytest.TempPathFactory) -> Generator[str]:
    """
    Yield a path to a fresh temporary SQLite file.
    Automatically cleaned up after the test.
    """
    db_file = str(tmp_path / "test_generator.db")
    yield db_file


@pytest.fixture()
def db_conn(tmp_db: str) -> Generator[sqlite3.Connection]:
    """Open and yield a SQLite connection to the temp DB; close on teardown."""
    conn = sqlite3.connect(tmp_db)
    conn.execute("PRAGMA journal_mode=WAL")
    yield conn
    conn.close()


# ── Minimal RawDocument factory ────────────────────────────────────────────────


def make_raw_doc(
    *,
    title: str = "Flash Attention 3: Optimizing Transformer Inference at Scale",
    url: str = "https://example.com/flash-attention-3",
    body: str | None = None,
    source: str = "arxiv",
    source_id: str | None = "2401.12345",
) -> dict:
    """
    Return a dict suitable for ``RawDocument.model_validate()``.
    Default body is >300 words to pass the word-count validator.
    """
    if body is None:
        body = " ".join(["word"] * 320)  # 320 words — passes MIN_WORDS=100
    return {
        "title": title,
        "url": url,
        "body": body,
        "source": source,
        "source_id": source_id,
    }


# ── Mock Gemini response factory ───────────────────────────────────────────────


def make_gemini_response(text: str) -> MagicMock:
    """Return a mock object whose .text attribute returns *text*."""
    mock = MagicMock()
    mock.text = text
    return mock
