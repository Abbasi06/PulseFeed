"""
Integration tests for GET /feed/{user_id}/brief.

Covers: 401/403/404 guards, cache hit/miss, TTL boundary,
brief invalidation on feed refresh, and 502 propagation.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from models import FeedBrief, FeedItem
from tests.conftest import USER_A, USER_B


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_BRIEF = {
    "user_id": 0,  # overwritten per test
    "headline": "AI dominates the week",
    "signals": ["LLM adoption accelerating", "Open-source momentum growing"],
    "top_reads": [{"title": "GPT-5 Announced", "url": "https://ex.com", "source": "OpenAI"}],
    "watch": ["Gemini Ultra", "Claude 4"],
}


def _insert_feed_item(db: Session, user_id: int) -> FeedItem:
    item = FeedItem(
        user_id=user_id,
        title="AI News",
        summary="Summary",
        source="Src",
        url="https://example.com",
        topic="AI",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _insert_brief(
    db: Session, user_id: int, seconds_old: float = 0
) -> FeedBrief:
    brief = FeedBrief(
        user_id=user_id,
        headline="Cached headline",
        signals=["signal 1"],
        top_reads=[{"title": "T", "url": "#", "source": "S"}],
        watch=["watch 1"],
        generated_at=datetime.now(timezone.utc) - timedelta(seconds=seconds_old),
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)
    return brief


def _mock_brief(user_id: int) -> dict:
    return {**_MOCK_BRIEF, "user_id": user_id}


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------


def test_brief_requires_auth(client: TestClient) -> None:
    # No cookie set → 401
    assert client.get("/feed/1/brief").status_code == 401


def test_brief_wrong_user_returns_403(client: TestClient, db: Session) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    client.post("/users", json=USER_B)  # cookie now belongs to B
    assert client.get(f"/feed/{user_a_id}/brief").status_code == 403


def test_brief_forged_token_for_other_user_returns_403(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    user_b_id = client.post("/users", json=USER_B).json()["id"]
    client.cookies.set("access_token", create_access_token(user_a_id))
    assert client.get(f"/feed/{user_b_id}/brief").status_code == 403


# ---------------------------------------------------------------------------
# 404 guard: no feed items
# ---------------------------------------------------------------------------


def test_brief_returns_404_when_no_feed_items(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    # No feed items created
    assert client.get(f"/feed/{user_id}/brief").status_code == 404


def test_brief_returns_404_for_nonexistent_user(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    # Forge a token for a user that does not exist
    client.cookies.set("access_token", create_access_token(99999))
    assert client.get("/feed/99999/brief").status_code == 404


# ---------------------------------------------------------------------------
# Cache hit — stale brief triggers regeneration
# ---------------------------------------------------------------------------


def test_brief_cache_hit_not_stale_no_generate_call(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)
    _insert_brief(db, user_id, seconds_old=6 * 3600 - 10)  # 10 s fresh

    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as m:
        resp = client.get(f"/feed/{user_id}/brief")

    assert resp.status_code == 200
    assert resp.json()["headline"] == "Cached headline"
    m.assert_not_called()


def test_brief_cache_stale_triggers_regeneration(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)
    _insert_brief(db, user_id, seconds_old=6 * 3600 + 10)  # 10 s stale

    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as m:
        m.return_value = _mock_brief(user_id)
        resp = client.get(f"/feed/{user_id}/brief")

    assert resp.status_code == 200
    m.assert_called_once()
    assert resp.json()["headline"] == "AI dominates the week"


def test_brief_no_cached_brief_generates_new_one(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)

    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as m:
        m.return_value = _mock_brief(user_id)
        resp = client.get(f"/feed/{user_id}/brief")

    assert resp.status_code == 200
    m.assert_called_once()
    data = resp.json()
    assert data["signals"] == ["LLM adoption accelerating", "Open-source momentum growing"]
    assert len(data["top_reads"]) == 1
    assert data["watch"] == ["Gemini Ultra", "Claude 4"]


# ---------------------------------------------------------------------------
# Brief invalidation when feed is refreshed
# ---------------------------------------------------------------------------


def test_brief_invalidated_on_feed_refresh(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)
    _insert_brief(db, user_id, seconds_old=0)  # fresh brief

    feed_payload = [
        {
            "user_id": user_id,
            "title": "New Article",
            "summary": "S",
            "source": "Src",
            "url": "https://example.com/1",
            "topic": "T",
            "published_date": "2026-01-01",
        }
    ]
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as m:
        m.return_value = feed_payload
        client.post(f"/feed/{user_id}/refresh")

    # Brief must have been deleted
    db.expire_all()
    remaining = db.query(FeedBrief).filter(FeedBrief.user_id == user_id).first()
    assert remaining is None


def test_brief_after_refresh_requires_regeneration(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)
    _insert_brief(db, user_id, seconds_old=0)

    feed_payload = [
        {
            "user_id": user_id,
            "title": "Fresh",
            "summary": "S",
            "source": "Src",
            "url": "https://example.com/1",
            "topic": "T",
            "published_date": "2026-01-01",
        }
    ]
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mf:
        mf.return_value = feed_payload
        client.post(f"/feed/{user_id}/refresh")

    # Now fetching brief must regenerate
    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as mb:
        mb.return_value = _mock_brief(user_id)
        resp = client.get(f"/feed/{user_id}/brief")

    assert resp.status_code == 200
    mb.assert_called_once()


# ---------------------------------------------------------------------------
# 502 propagation
# ---------------------------------------------------------------------------


def test_brief_502_when_agent_raises(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)

    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as m:
        m.side_effect = ValueError("GEMINI_API_KEY is not set in environment")
        resp = client.get(f"/feed/{user_id}/brief")

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


def test_brief_response_contains_all_required_fields(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)

    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as m:
        m.return_value = _mock_brief(user_id)
        resp = client.get(f"/feed/{user_id}/brief")

    assert resp.status_code == 200
    data = resp.json()
    for key in ("id", "user_id", "headline", "signals", "top_reads", "watch", "generated_at"):
        assert key in data, f"Missing key: {key}"


def test_brief_top_reads_contain_title_url_source(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)

    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as m:
        m.return_value = _mock_brief(user_id)
        resp = client.get(f"/feed/{user_id}/brief")

    top = resp.json()["top_reads"][0]
    assert "title" in top
    assert "url" in top
    assert "source" in top


# ---------------------------------------------------------------------------
# Second call within TTL reuses cached brief (no second generate call)
# ---------------------------------------------------------------------------


def test_brief_second_call_within_ttl_uses_cache(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_feed_item(db, user_id)

    with patch("agents.research_agent.generate_brief", new_callable=AsyncMock) as m:
        m.return_value = _mock_brief(user_id)
        client.get(f"/feed/{user_id}/brief")  # first call — generates
        client.get(f"/feed/{user_id}/brief")  # second call — cache hit

    m.assert_called_once()  # only one actual generation
