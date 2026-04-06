"""
Tests for dead-letter admin routes:
  GET    /admin/dead-letter
  POST   /admin/dead-letter/{index}/retry
  DELETE /admin/dead-letter

Redis is mocked in all tests.
"""

import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from admin_api.main import app

client = TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})

_KEY = "pulsegen:dead_letter:storage"

_SAMPLE_ITEM = json.dumps({
    "url": "https://example.com/doc",
    "title": "Test Document",
    "source": "arxiv",
    "error": "DB timeout",
    "failed_at": "2024-01-15T12:00:00",
})


def _make_redis(
    items: list[str] | None = None,
    total_count: int | None = None,
) -> MagicMock:
    items = items or [_SAMPLE_ITEM]
    total_count = total_count if total_count is not None else len(items)
    mock = MagicMock()
    mock.lrange.return_value = items
    mock.llen.return_value = total_count
    mock.lindex.return_value = items[0] if items else None
    mock.delete.return_value = 1
    return mock


class TestGetDeadLetter:
    def test_returns_200(self) -> None:
        with patch("admin_api.routes.dead_letter._get_redis", return_value=_make_redis()):
            resp = client.get("/admin/dead-letter")
        assert resp.status_code == 200

    def test_items_and_count_returned(self) -> None:
        with patch("admin_api.routes.dead_letter._get_redis", return_value=_make_redis()):
            resp = client.get("/admin/dead-letter")
        data = resp.json()
        assert "items" in data
        assert "count" in data
        assert data["count"] == 1

    def test_item_fields_parsed(self) -> None:
        with patch("admin_api.routes.dead_letter._get_redis", return_value=_make_redis()):
            resp = client.get("/admin/dead-letter")
        item = resp.json()["items"][0]
        assert item["url"] == "https://example.com/doc"
        assert item["error"] == "DB timeout"
        assert item["source"] == "arxiv"

    def test_malformed_item_skipped(self) -> None:
        items = ["not-valid-json", _SAMPLE_ITEM]
        with patch("admin_api.routes.dead_letter._get_redis", return_value=_make_redis(items=items, total_count=2)):
            resp = client.get("/admin/dead-letter")
        # Malformed item is skipped; only 1 valid item returned
        assert len(resp.json()["items"]) == 1

    def test_redis_unavailable_returns_empty(self) -> None:
        with patch("admin_api.routes.dead_letter._get_redis", return_value=None):
            resp = client.get("/admin/dead-letter")
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["count"] == 0

    def test_limit_param_respected(self) -> None:
        mock_redis = _make_redis()
        with patch("admin_api.routes.dead_letter._get_redis", return_value=mock_redis):
            client.get("/admin/dead-letter?limit=10")
        mock_redis.lrange.assert_called_once_with(_KEY, 0, 9)

    def test_limit_capped_at_500(self) -> None:
        mock_redis = _make_redis()
        with patch("admin_api.routes.dead_letter._get_redis", return_value=mock_redis):
            client.get("/admin/dead-letter?limit=9999")
        # lrange called with end index = 499
        mock_redis.lrange.assert_called_once_with(_KEY, 0, 499)


class TestRetryDeadLetterItem:
    def test_returns_200_with_status_queued(self) -> None:
        with patch("admin_api.routes.dead_letter._get_redis", return_value=_make_redis()):
            resp = client.post("/admin/dead-letter/0/retry")
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"

    def test_url_returned_in_response(self) -> None:
        with patch("admin_api.routes.dead_letter._get_redis", return_value=_make_redis()):
            resp = client.post("/admin/dead-letter/0/retry")
        assert "https://example.com/doc" in resp.json()["url"]

    def test_item_not_found_returns_404(self) -> None:
        mock = _make_redis()
        mock.lindex.return_value = None
        with patch("admin_api.routes.dead_letter._get_redis", return_value=mock):
            resp = client.post("/admin/dead-letter/99/retry")
        assert resp.status_code == 404

    def test_redis_unavailable_returns_503(self) -> None:
        with patch("admin_api.routes.dead_letter._get_redis", return_value=None):
            resp = client.post("/admin/dead-letter/0/retry")
        assert resp.status_code == 503


class TestClearDeadLetter:
    def test_returns_200_with_cleared_status(self) -> None:
        mock = _make_redis(total_count=7)
        with patch("admin_api.routes.dead_letter._get_redis", return_value=mock):
            resp = client.delete("/admin/dead-letter")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cleared"

    def test_count_in_response(self) -> None:
        mock = _make_redis(total_count=42)
        with patch("admin_api.routes.dead_letter._get_redis", return_value=mock):
            resp = client.delete("/admin/dead-letter")
        assert resp.json()["count"] == 42

    def test_delete_called_on_redis(self) -> None:
        mock = _make_redis()
        with patch("admin_api.routes.dead_letter._get_redis", return_value=mock):
            client.delete("/admin/dead-letter")
        mock.delete.assert_called_once_with(_KEY)

    def test_redis_unavailable_returns_503(self) -> None:
        with patch("admin_api.routes.dead_letter._get_redis", return_value=None):
            resp = client.delete("/admin/dead-letter")
        assert resp.status_code == 503
