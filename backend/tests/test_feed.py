from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import FeedItem
from tests.conftest import USER_A, USER_B


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_items(user_id: int) -> list[dict]:
    return [
        {
            "user_id": user_id,
            "title": "AI Breakthrough",
            "summary": "Researchers made a major discovery.",
            "source": "Tech Blog",
            "url": "https://example.com/ai",
            "topic": "AI",
            "published_date": "2026-01-01",
        }
    ]


def _insert_feed_item(db: Session, user_id: int, hours_old: float = 0) -> FeedItem:
    fetched_at = datetime.utcnow() - timedelta(hours=hours_old)
    item = FeedItem(
        user_id=user_id,
        title="Cached Article",
        summary="Some summary",
        source="Source",
        url="https://example.com",
        topic="General",
        fetched_at=fetched_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# GET /feed/{user_id}
# ---------------------------------------------------------------------------


def test_get_feed_unauthenticated_401(client: TestClient) -> None:
    assert client.get("/feed/1").status_code == 401


def test_get_feed_forbidden_when_other_user(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    client.post("/users", json=USER_B)  # cookie now belongs to B
    assert client.get(f"/feed/{user_a_id}").status_code == 403


def test_get_feed_user_not_found_404(client: TestClient) -> None:
    # Auth check runs before DB lookup, so we must carry a token for the
    # same user_id we're requesting — forge one for a non-existent user.
    from auth import create_access_token
    client.cookies.set("access_token", create_access_token(99999))
    assert client.get("/feed/99999").status_code == 404


def test_get_feed_triggers_agent_when_no_cache(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_items(user_id)
        resp = client.get(f"/feed/{user_id}")
    assert resp.status_code == 200
    mock_gen.assert_called_once()
    assert resp.json()[0]["title"] == "AI Breakthrough"


def test_get_feed_returns_cache_when_fresh(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id, hours_old=1)  # 1 hour old — fresh
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        resp = client.get(f"/feed/{user_id}")
    assert resp.status_code == 200
    mock_gen.assert_not_called()
    assert resp.json()[0]["title"] == "Cached Article"


def test_get_feed_refreshes_when_stale(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id, hours_old=7)  # 7 hours old — stale
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_items(user_id)
        resp = client.get(f"/feed/{user_id}")
    assert resp.status_code == 200
    mock_gen.assert_called_once()
    assert resp.json()[0]["title"] == "AI Breakthrough"


# ---------------------------------------------------------------------------
# POST /feed/{user_id}/refresh
# ---------------------------------------------------------------------------


def test_refresh_feed_always_calls_agent(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id, hours_old=1)  # cache is fresh — still refreshes
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_items(user_id)
        resp = client.post(f"/feed/{user_id}/refresh")
    assert resp.status_code == 200
    mock_gen.assert_called_once()


def test_refresh_feed_replaces_old_items(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_items(user_id)
        resp = client.post(f"/feed/{user_id}/refresh")
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()]
    assert "Cached Article" not in titles
    assert "AI Breakthrough" in titles


def test_refresh_feed_forbidden_when_other_user(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    client.post("/users", json=USER_B)
    assert client.post(f"/feed/{user_a_id}/refresh").status_code == 403


def test_refresh_feed_502_on_agent_failure(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = RuntimeError("API down")
        resp = client.post(f"/feed/{user_id}/refresh")
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# PATCH /feed/items/{item_id}/like
# ---------------------------------------------------------------------------


def test_toggle_like_sets_liked(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_id)
    resp = client.patch(f"/feed/items/{item.id}/like")
    assert resp.status_code == 200
    assert resp.json()["liked"] is True


def test_toggle_like_twice_reverts(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_id)
    client.patch(f"/feed/items/{item.id}/like")
    resp = client.patch(f"/feed/items/{item.id}/like")
    assert resp.json()["liked"] is False


def test_toggle_like_forbidden_when_other_user(client: TestClient, db: Session) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_a_id)
    client.post("/users", json=USER_B)  # switch to user B
    assert client.patch(f"/feed/items/{item.id}/like").status_code == 403


def test_toggle_like_not_found_404(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    assert client.patch("/feed/items/99999/like").status_code == 404
