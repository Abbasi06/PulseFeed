"""
Tests for src/pipeline/dedup.py — URL deduplication against PostgreSQL.
All psycopg2 calls are mocked — no real DB connection.

dedup.py imports psycopg2 locally inside is_duplicate(), so we patch
psycopg2.connect at the psycopg2 module level (not via the dedup module).
"""

from unittest.mock import MagicMock, patch

from src.pipeline.dedup import compute_url_hash, is_duplicate


def _mock_settings(db_url: str = "postgresql://test/db") -> MagicMock:
    m = MagicMock()
    m.storage_database_url = db_url
    return m


class TestComputeUrlHash:
    def test_returns_64_char_hex(self) -> None:
        h = compute_url_hash("https://example.com/article")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self) -> None:
        url = "https://arxiv.org/abs/2401.12345"
        assert compute_url_hash(url) == compute_url_hash(url)

    def test_different_urls_produce_different_hashes(self) -> None:
        h1 = compute_url_hash("https://example.com/a")
        h2 = compute_url_hash("https://example.com/b")
        assert h1 != h2

    def test_empty_string_hashes(self) -> None:
        h = compute_url_hash("")
        assert len(h) == 64

    def test_same_path_different_scheme_different_hash(self) -> None:
        h1 = compute_url_hash("http://example.com/page")
        h2 = compute_url_hash("https://example.com/page")
        assert h1 != h2


class TestIsDuplicate:
    def _mock_conn(self, exists: bool) -> MagicMock:
        """Build a mock psycopg2 connection that returns one row or nothing."""
        mock_cur = MagicMock()
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchone.return_value = (1,) if exists else None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        return mock_conn

    def test_returns_true_when_url_already_stored(self) -> None:
        with (
            patch("psycopg2.connect") as mock_connect,
            patch("src.pipeline.dedup.settings", _mock_settings()),
        ):
            mock_connect.return_value = self._mock_conn(exists=True)
            assert is_duplicate("https://example.com/already-stored") is True

    def test_returns_false_when_url_is_new(self) -> None:
        with (
            patch("psycopg2.connect") as mock_connect,
            patch("src.pipeline.dedup.settings", _mock_settings()),
        ):
            mock_connect.return_value = self._mock_conn(exists=False)
            assert is_duplicate("https://example.com/new-article") is False

    def test_fail_open_on_connection_error(self) -> None:
        """psycopg2 connection errors should fail-open (return False)."""
        with (
            patch("psycopg2.connect") as mock_connect,
            patch("src.pipeline.dedup.settings", _mock_settings("postgresql://bad/db")),
        ):
            mock_connect.side_effect = Exception("connection refused")
            assert is_duplicate("https://example.com/any") is False

    def test_correct_url_hash_is_queried(self) -> None:
        """Verify the SQL query uses the hash of the URL, not the raw URL."""
        with (
            patch("psycopg2.connect") as mock_connect,
            patch("src.pipeline.dedup.settings", _mock_settings()),
        ):
            mock_conn = self._mock_conn(exists=False)
            mock_connect.return_value = mock_conn
            url = "https://example.com/test"

            is_duplicate(url)

            mock_cur = mock_conn.cursor.return_value.__enter__.return_value
            call_args = mock_cur.execute.call_args
            sql, params = call_args[0]
            expected_hash = compute_url_hash(url)
            assert expected_hash in params

    def test_connection_timeout_param_passed(self) -> None:
        """Ensure connect_timeout=5 is forwarded to psycopg2.connect."""
        with (
            patch("psycopg2.connect") as mock_connect,
            patch("src.pipeline.dedup.settings", _mock_settings()),
        ):
            mock_connect.return_value = self._mock_conn(exists=False)
            is_duplicate("https://example.com/test")
            _, kwargs = mock_connect.call_args
            assert kwargs.get("connect_timeout") == 5
