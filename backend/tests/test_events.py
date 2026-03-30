import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import Event
from tests.conftest import USER_A, USER_B


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_events(user_id: int) -> list[dict]:
    return [
        {
            "user_id": user_id,
            "name": "PyCon 2026",
            "date": "2026-05-15",
            "location": "Pittsburgh, PA",
            "type": "Conference",
            "url": "https://us.pycon.org",
            "reason": "Largest Python conference in North America.",
        }
    ]


def _insert_event(db: Session, user_id: int, hours_old: float = 0) -> Event:
    fetched_at = datetime.now(timezone.utc) - timedelta(hours=hours_old)
    ev = Event(
        user_id=user_id,
        name="Cached Event",
        date="2026-04-01",
        fetched_at=fetched_at,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


# ---------------------------------------------------------------------------
# GET /events/{user_id}
# ---------------------------------------------------------------------------


def test_get_events_unauthenticated_401(client: TestClient) -> None:
    assert client.get("/events/1").status_code == 401


def test_get_events_forbidden_when_other_user(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    client.post("/users", json=USER_B)
    assert client.get(f"/events/{user_a_id}").status_code == 403


def test_get_events_user_not_found_404(client: TestClient) -> None:
    # Auth check runs before DB lookup, so we must carry a token for the
    # same user_id we're requesting — forge one for a non-existent user.
    from auth import create_access_token
    client.cookies.set("access_token", create_access_token(99999))
    assert client.get("/events/99999").status_code == 404


def test_get_events_triggers_agent_when_no_cache(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_events(user_id)
        resp = client.get(f"/events/{user_id}")
    assert resp.status_code == 200
    # Background task is queued; response returns immediately with empty list + header
    assert resp.headers.get("X-Events-Generating") == "true"
    assert isinstance(resp.json(), list)
    mock_gen.assert_called_once()


def test_get_events_returns_cache_when_fresh(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_event(db, user_id, hours_old=1)
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        resp = client.get(f"/events/{user_id}")
    assert resp.status_code == 200
    mock_gen.assert_not_called()
    assert resp.json()[0]["name"] == "Cached Event"


def test_get_events_refreshes_when_stale(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_event(db, user_id, hours_old=7)
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_events(user_id)
        resp = client.get(f"/events/{user_id}")
    assert resp.status_code == 200
    # Stale items returned immediately with background refresh queued
    assert resp.headers.get("X-Events-Generating") == "true"
    assert resp.json()[0]["name"] == "Cached Event"
    mock_gen.assert_called_once()


# ---------------------------------------------------------------------------
# POST /events/{user_id}/refresh
# ---------------------------------------------------------------------------


def test_refresh_events_always_calls_agent(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_event(db, user_id, hours_old=1)
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_events(user_id)
        resp = client.post(f"/events/{user_id}/refresh")
    assert resp.status_code == 200
    mock_gen.assert_called_once()


def test_refresh_events_replaces_old_items(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_event(db, user_id)
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_events(user_id)
        resp = client.post(f"/events/{user_id}/refresh")
    names = [ev["name"] for ev in resp.json()]
    assert "Cached Event" not in names
    assert "PyCon 2026" in names


def test_refresh_events_forbidden_when_other_user(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    client.post("/users", json=USER_B)
    assert client.post(f"/events/{user_a_id}/refresh").status_code == 403


def test_refresh_events_502_on_agent_failure(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = RuntimeError("API down")
        assert client.post(f"/events/{user_id}/refresh").status_code == 502


# ---------------------------------------------------------------------------
# PATCH /events/items/{item_id}/like
# ---------------------------------------------------------------------------


def test_toggle_event_like_sets_liked(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    ev = _insert_event(db, user_id)
    resp = client.patch(f"/events/items/{ev.id}/like")
    assert resp.status_code == 200
    assert resp.json()["liked"] is True


def test_toggle_event_like_twice_reverts(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    ev = _insert_event(db, user_id)
    client.patch(f"/events/items/{ev.id}/like")
    resp = client.patch(f"/events/items/{ev.id}/like")
    assert resp.json()["liked"] is False


def test_toggle_event_like_forbidden_when_other_user(client: TestClient, db: Session) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    ev = _insert_event(db, user_a_id)
    client.post("/users", json=USER_B)
    assert client.patch(f"/events/items/{ev.id}/like").status_code == 403


def test_toggle_event_like_not_found_404(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    assert client.patch("/events/items/99999/like").status_code == 404


# ---------------------------------------------------------------------------
# POST /events/{user_id}/refresh — edge cases
# ---------------------------------------------------------------------------


def test_refresh_events_preserves_existing_when_generation_returns_empty(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_event(db, user_id)
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = []  # agent returns nothing
        resp = client.post(f"/events/{user_id}/refresh")
    assert resp.status_code == 200
    names = [ev["name"] for ev in resp.json()]
    assert "Cached Event" in names


def test_refresh_events_504_on_timeout(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = asyncio.TimeoutError()
        resp = client.post(f"/events/{user_id}/refresh")
    assert resp.status_code == 504


def test_refresh_events_cooldown_429(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_events(user_id)
        client.post(f"/events/{user_id}/refresh")  # first — sets cooldown
        resp = client.post(f"/events/{user_id}/refresh")  # second within 60s
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
