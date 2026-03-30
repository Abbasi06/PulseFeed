import asyncio
from datetime import datetime, timedelta, timezone
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
    fetched_at = datetime.now(timezone.utc) - timedelta(hours=hours_old)
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
    # Background task is queued; response returns immediately with empty list + header
    assert resp.headers.get("X-Feed-Generating") == "true"
    assert isinstance(resp.json(), list)
    mock_gen.assert_called_once()


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
    # Stale items returned immediately with background refresh queued
    assert resp.headers.get("X-Feed-Generating") == "true"
    assert resp.json()[0]["title"] == "Cached Article"
    mock_gen.assert_called_once()


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


# ---------------------------------------------------------------------------
# POST /feed/{user_id}/refresh — edge cases
# ---------------------------------------------------------------------------


def test_refresh_feed_preserves_existing_when_generation_returns_empty(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = []  # agent returns nothing
        resp = client.post(f"/feed/{user_id}/refresh")
    assert resp.status_code == 200
    # Existing item must still be there
    titles = [item["title"] for item in resp.json()]
    assert "Cached Article" in titles


def test_refresh_feed_504_on_timeout(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = asyncio.TimeoutError()
        resp = client.post(f"/feed/{user_id}/refresh")
    assert resp.status_code == 504


def test_refresh_feed_cooldown_429(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_items(user_id)
        client.post(f"/feed/{user_id}/refresh")  # first refresh — sets cooldown
        resp = client.post(f"/feed/{user_id}/refresh")  # second within 60s
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


# ---------------------------------------------------------------------------
# PATCH /feed/items/{item_id}/dislike
# ---------------------------------------------------------------------------


def test_toggle_dislike_sets_disliked(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_id)
    resp = client.patch(f"/feed/items/{item.id}/dislike")
    assert resp.status_code == 200
    assert resp.json()["disliked"] is True


def test_toggle_dislike_twice_reverts(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_id)
    client.patch(f"/feed/items/{item.id}/dislike")
    resp = client.patch(f"/feed/items/{item.id}/dislike")
    assert resp.json()["disliked"] is False


def test_toggle_dislike_forbidden_403(client: TestClient, db: Session) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_a_id)
    client.post("/users", json=USER_B)
    assert client.patch(f"/feed/items/{item.id}/dislike").status_code == 403


def test_toggle_dislike_not_found_404(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    assert client.patch("/feed/items/99999/dislike").status_code == 404


# ---------------------------------------------------------------------------
# PATCH /feed/items/{item_id}/save
# ---------------------------------------------------------------------------


def test_toggle_save_sets_saved(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_id)
    resp = client.patch(f"/feed/items/{item.id}/save")
    assert resp.status_code == 200
    assert resp.json()["saved"] is True


def test_toggle_save_twice_reverts(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_id)
    client.patch(f"/feed/items/{item.id}/save")
    resp = client.patch(f"/feed/items/{item.id}/save")
    assert resp.json()["saved"] is False


def test_toggle_save_forbidden_403(client: TestClient, db: Session) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_a_id)
    client.post("/users", json=USER_B)
    assert client.patch(f"/feed/items/{item.id}/save").status_code == 403


def test_toggle_save_not_found_404(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    assert client.patch("/feed/items/99999/save").status_code == 404


# ---------------------------------------------------------------------------
# POST /feed/items/{item_id}/click
# ---------------------------------------------------------------------------


def test_record_click_increments_read_count(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_id)
    resp = client.post(f"/feed/items/{item.id}/click")
    assert resp.status_code == 200
    assert resp.json()["read_count"] == 1


def test_record_click_multiple_times_accumulates(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_id)
    for _ in range(3):
        client.post(f"/feed/items/{item.id}/click")
    resp = client.post(f"/feed/items/{item.id}/click")
    assert resp.json()["read_count"] == 4


def test_record_click_forbidden_403(client: TestClient, db: Session) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_feed_item(db, user_a_id)
    client.post("/users", json=USER_B)
    assert client.post(f"/feed/items/{item.id}/click").status_code == 403


def test_record_click_not_found_404(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    assert client.post("/feed/items/99999/click").status_code == 404


# ---------------------------------------------------------------------------
# GET /feed/{user_id}/brief
# ---------------------------------------------------------------------------


def _mock_brief_data(user_id: int) -> dict:
    return {
        "user_id": user_id,
        "headline": "AI is transforming software engineering",
        "signals": ["LLM adoption rising", "Open-source models closing gap"],
        "top_reads": [{"title": "AI News", "url": "https://example.com", "source": "TechBlog"}],
        "watch": ["OpenAI", "Anthropic"],
    }


def test_get_brief_404_when_no_feed(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    resp = client.get(f"/feed/{user_id}/brief")
    assert resp.status_code == 404
    assert "feed" in resp.json()["detail"].lower()


def test_get_brief_generates_when_no_cached_brief(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)
    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as mock_brief:
        mock_brief.return_value = _mock_brief_data(user_id)
        resp = client.get(f"/feed/{user_id}/brief")
    assert resp.status_code == 200
    assert resp.json()["headline"] == "AI is transforming software engineering"
    mock_brief.assert_called_once()


def test_get_brief_returns_cached_when_fresh(client: TestClient, db: Session) -> None:
    from datetime import datetime, timezone
    from models import FeedBrief

    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)
    cached_brief = FeedBrief(
        user_id=user_id,
        headline="Cached headline",
        signals=["signal1"],
        top_reads=[],
        watch=[],
        generated_at=datetime.now(timezone.utc),  # fresh
    )
    db.add(cached_brief)
    db.commit()

    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as mock_brief:
        resp = client.get(f"/feed/{user_id}/brief")
    assert resp.status_code == 200
    assert resp.json()["headline"] == "Cached headline"
    mock_brief.assert_not_called()


def test_get_brief_forbidden_403(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    client.post("/users", json=USER_B)
    assert client.get(f"/feed/{user_a_id}/brief").status_code == 403
