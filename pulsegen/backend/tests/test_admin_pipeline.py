"""
Tests for pipeline admin routes:
  GET  /admin/pipeline/status
  POST /admin/pipeline/run-now

Redis and Celery are mocked.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from admin_api.main import app

client = TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})


def _make_redis(queue_depth: int = 5) -> MagicMock:
    mock_redis = MagicMock()
    mock_redis.llen.return_value = queue_depth
    return mock_redis


class TestGetPipelineStatus:
    def test_returns_200(self) -> None:
        with patch("admin_api.routes.pipeline._get_redis", return_value=_make_redis()):
            resp = client.get("/admin/pipeline/status")
        assert resp.status_code == 200

    def test_queue_depth_returned(self) -> None:
        with patch("admin_api.routes.pipeline._get_redis", return_value=_make_redis(queue_depth=12)):
            resp = client.get("/admin/pipeline/status")
        assert resp.json()["queue_depth"] == 12

    def test_redis_unavailable_returns_zero_depth(self) -> None:
        with patch("admin_api.routes.pipeline._get_redis", return_value=None):
            resp = client.get("/admin/pipeline/status")
        assert resp.status_code == 200
        assert resp.json()["queue_depth"] == 0

    def test_last_run_field_present(self) -> None:
        with patch("admin_api.routes.pipeline._get_redis", return_value=_make_redis()):
            resp = client.get("/admin/pipeline/status")
        assert "last_run" in resp.json()

    def test_redis_exception_returns_zero_depth(self) -> None:
        mock_redis = MagicMock()
        mock_redis.llen.side_effect = Exception("connection reset")
        with patch("admin_api.routes.pipeline._get_redis", return_value=mock_redis):
            resp = client.get("/admin/pipeline/status")
        assert resp.status_code == 200
        assert resp.json()["queue_depth"] == 0


class TestRunPipelineNow:
    def test_returns_accepted_true(self) -> None:
        mock_celery = MagicMock()
        mock_celery.send_task.return_value = MagicMock()
        with patch("admin_api.routes.pipeline.celery_app", mock_celery, create=True), \
             patch("src.celery_app.app", mock_celery, create=True):
            # Patch the import inside the function
            with patch("admin_api.routes.pipeline.__import__", side_effect=None, create=True):
                pass
        # Simpler: patch the module-level import path used in the route
        with patch("src.celery_app.app") as mock_app:
            mock_app.send_task.return_value = MagicMock(id="fake-task-id")
            resp = client.post("/admin/pipeline/run-now")
        assert resp.status_code == 200
        assert resp.json()["accepted"] is True

    def test_celery_failure_returns_500(self) -> None:
        with patch("src.celery_app.app") as mock_app:
            mock_app.send_task.side_effect = Exception("broker unreachable")
            resp = client.post("/admin/pipeline/run-now")
        assert resp.status_code == 500

    def test_message_contains_harvest_cycle(self) -> None:
        with patch("src.celery_app.app") as mock_app:
            mock_app.send_task.return_value = MagicMock(id="tid")
            resp = client.post("/admin/pipeline/run-now")
        assert "harvest_cycle" in resp.json()["message"]
