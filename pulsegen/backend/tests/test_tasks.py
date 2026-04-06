"""
Tests for src/tasks.py helpers — _dead_letter, _record_stored_tags,
_load_last_cycle_tag_counts.

Celery tasks themselves are tested via their helper functions.
All Redis and SQLite calls are either mocked or use tmp_db.
"""

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from src.schemas import DataSource, StoragePayload

# ── Shared fixture for StoragePayload ─────────────────────────────────────────


def _make_payload(url: str = "https://example.com/test") -> StoragePayload:
    return StoragePayload(
        source=DataSource.ARXIV,
        url=url,
        url_hash="abc" * 21 + "d",  # 64 chars
        content_hash="def" * 21 + "g",
        title="Test Document Title",
        summary="Three sentence summary here. Second sentence. Third sentence.",
        bm25_keywords=["Flash", "Attention", "CUDA", "Triton", "BF16"],
        taxonomy_tags=["AI Engineering"],
        gatekeeper_confidence=0.88,
        processed_at=datetime.now(UTC),
    )


# ── _dead_letter ───────────────────────────────────────────────────────────────


class TestDeadLetter:
    def test_pushes_to_redis_key(self) -> None:
        from src.tasks import _dead_letter

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 1

        with patch("src.tasks.redis_lib") as mock_lib:
            mock_lib.from_url.return_value = mock_redis
            _dead_letter(_make_payload(), "DB timeout")

        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args[0]
        key = call_args[0]
        payload_json = json.loads(call_args[1])

        assert key == "pulsegen:dead_letter:storage"
        assert payload_json["url"] == "https://example.com/test"
        assert payload_json["error"] == "DB timeout"

    def test_trims_queue_to_500(self) -> None:
        from src.tasks import _dead_letter

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 50

        with patch("src.tasks.redis_lib") as mock_lib:
            mock_lib.from_url.return_value = mock_redis
            _dead_letter(_make_payload(), "timeout")

        mock_redis.ltrim.assert_called_once_with("pulsegen:dead_letter:storage", 0, 499)

    def test_logs_critical_on_redis_failure(self) -> None:
        from src.tasks import _dead_letter

        with patch("src.tasks.redis_lib") as mock_lib:
            mock_lib.from_url.side_effect = Exception("Redis down")
            with patch("src.tasks.logger") as mock_log:
                _dead_letter(_make_payload(), "some error")
                mock_log.critical.assert_called_once()

    def test_logs_critical_when_queue_large(self) -> None:
        from src.tasks import _dead_letter

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 150  # > 100 threshold

        with patch("src.tasks.redis_lib") as mock_lib:
            mock_lib.from_url.return_value = mock_redis
            with patch("src.tasks.logger") as mock_log:
                _dead_letter(_make_payload(), "error")
                mock_log.critical.assert_called()

    def test_does_not_raise_when_redis_down(self) -> None:
        """_dead_letter must not propagate exceptions."""
        from src.tasks import _dead_letter

        with patch("src.tasks.redis_lib") as mock_lib:
            mock_lib.from_url.side_effect = ConnectionError("unreachable")
            # Should not raise
            _dead_letter(_make_payload(), "storage failed")


# ── _record_stored_tags ────────────────────────────────────────────────────────


class TestRecordStoredTags:
    def test_inserts_tags_into_sqlite(self, tmp_db: str) -> None:
        from src.tasks import _record_stored_tags

        with patch("src.tasks.settings") as ms:
            ms.generator_db_path = tmp_db
            _record_stored_tags(["AI Engineering", "MLOps"])

        conn = sqlite3.connect(tmp_db)
        rows = conn.execute("SELECT tag, count FROM current_cycle_tags").fetchall()
        conn.close()

        tag_map = {r[0]: r[1] for r in rows}
        assert tag_map["AI Engineering"] == 1
        assert tag_map["MLOps"] == 1

    def test_increments_existing_tag_count(self, tmp_db: str) -> None:
        from src.tasks import _record_stored_tags

        with patch("src.tasks.settings") as ms:
            ms.generator_db_path = tmp_db
            _record_stored_tags(["AI Engineering"])
            _record_stored_tags(["AI Engineering"])
            _record_stored_tags(["AI Engineering"])

        conn = sqlite3.connect(tmp_db)
        row = conn.execute(
            "SELECT count FROM current_cycle_tags WHERE tag = 'AI Engineering'"
        ).fetchone()
        conn.close()
        assert row[0] == 3

    def test_multiple_tags_recorded_in_one_call(self, tmp_db: str) -> None:
        from src.tasks import _record_stored_tags

        tags = ["AI Engineering", "Distributed Systems", "GPU Optimization"]
        with patch("src.tasks.settings") as ms:
            ms.generator_db_path = tmp_db
            _record_stored_tags(tags)

        conn = sqlite3.connect(tmp_db)
        rows = conn.execute("SELECT tag FROM current_cycle_tags").fetchall()
        conn.close()
        stored_tags = {r[0] for r in rows}
        assert stored_tags == set(tags)

    def test_empty_tags_is_no_op(self, tmp_db: str) -> None:
        from src.tasks import _record_stored_tags

        with patch("src.tasks.settings") as ms:
            ms.generator_db_path = tmp_db
            _record_stored_tags([])

        conn = sqlite3.connect(tmp_db)
        count = conn.execute("SELECT COUNT(*) FROM current_cycle_tags").fetchone()[0]
        conn.close()
        assert count == 0


# ── _load_last_cycle_tag_counts ────────────────────────────────────────────────


class TestLoadLastCycleTagCounts:
    def test_returns_dict_of_tag_counts(self, tmp_db: str) -> None:
        from src.tasks import _load_last_cycle_tag_counts, _record_stored_tags

        with patch("src.tasks.settings") as ms:
            ms.generator_db_path = tmp_db
            _record_stored_tags(["AI Engineering", "MLOps"])
            _record_stored_tags(["AI Engineering"])  # count → 2
            result = _load_last_cycle_tag_counts()

        assert result["AI Engineering"] == 2
        assert result["MLOps"] == 1

    def test_resets_table_after_load(self, tmp_db: str) -> None:
        from src.tasks import _load_last_cycle_tag_counts, _record_stored_tags

        with patch("src.tasks.settings") as ms:
            ms.generator_db_path = tmp_db
            _record_stored_tags(["AI Engineering"])
            _load_last_cycle_tag_counts()

            # After loading, the table should be empty
            conn = sqlite3.connect(tmp_db)
            count = conn.execute("SELECT COUNT(*) FROM current_cycle_tags").fetchone()[0]
            conn.close()

        assert count == 0

    def test_returns_empty_dict_on_fresh_db(self, tmp_db: str) -> None:
        from src.tasks import _load_last_cycle_tag_counts

        with patch("src.tasks.settings") as ms:
            ms.generator_db_path = tmp_db
            result = _load_last_cycle_tag_counts()

        assert result == {}

    def test_returns_empty_dict_on_error(self) -> None:
        from src.tasks import _load_last_cycle_tag_counts

        with patch("src.tasks.settings") as ms:
            ms.generator_db_path = "/nonexistent/path/that/cannot/exist.db"
            # Should not raise — returns {} on error
            result = _load_last_cycle_tag_counts()

        assert isinstance(result, dict)
