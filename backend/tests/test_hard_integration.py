"""
Hard integration and security tests.

These tests probe multi-step flows, JWT security edge cases, cross-user
isolation, cache-boundary timing, state-machine correctness (like toggle),
cascade deletes, and scenarios where the agent returns surprising output.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

import routes.feed as _feed_route
from auth import ALGORITHM, SECRET_KEY, create_access_token
from models import Event, FeedItem, User
from tests.conftest import USER_A, USER_B


# ---------------------------------------------------------------------------
# JWT / auth edge cases
# ---------------------------------------------------------------------------


def test_expired_jwt_returns_401(client: TestClient) -> None:
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    client.cookies.set("access_token", expired)
    assert client.get("/users/me").status_code == 401


def test_jwt_signed_with_wrong_secret_returns_401(client: TestClient) -> None:
    bad_token = jwt.encode({"sub": "1"}, "totally-wrong-secret", algorithm=ALGORITHM)
    client.cookies.set("access_token", bad_token)
    assert client.get("/users/me").status_code == 401


def test_jwt_with_non_integer_sub_returns_401(client: TestClient) -> None:
    # _decode_token does int(payload["sub"]) — "not-an-int" raises ValueError → 401
    bad_token = jwt.encode({"sub": "not-an-int"}, SECRET_KEY, algorithm=ALGORITHM)
    client.cookies.set("access_token", bad_token)
    assert client.get("/users/me").status_code == 401


def test_jwt_missing_sub_claim_returns_401(client: TestClient) -> None:
    # KeyError on payload["sub"] → 401
    bad_token = jwt.encode({"user_id": "1"}, SECRET_KEY, algorithm=ALGORITHM)
    client.cookies.set("access_token", bad_token)
    assert client.get("/users/me").status_code == 401


def test_tampered_jwt_payload_returns_401(client: TestClient) -> None:
    # A valid-looking token but with wrong signature (manually altered payload section)
    real_token = create_access_token(1)
    parts = real_token.split(".")
    # Replace the payload section with a base64-encoded different payload
    import base64
    import json
    fake_payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "9999"}).encode()
    ).rstrip(b"=").decode()
    tampered = f"{parts[0]}.{fake_payload}.{parts[2]}"
    client.cookies.set("access_token", tampered)
    assert client.get("/users/me").status_code == 401


def test_valid_jwt_for_deleted_user_returns_404(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    # Verify access works before deletion
    assert client.get("/users/me").status_code == 200
    # Delete user directly (no DELETE /users endpoint)
    user = db.get(User, user_id)
    db.delete(user)
    db.commit()
    # Cookie is still valid but the user no longer exists
    assert client.get("/users/me").status_code == 404


def test_empty_string_cookie_returns_401(client: TestClient) -> None:
    client.cookies.set("access_token", "")
    assert client.get("/users/me").status_code == 401


# ---------------------------------------------------------------------------
# Cross-user isolation (IDOR prevention)
# ---------------------------------------------------------------------------


def test_user_a_cannot_read_user_b_profile(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    user_b_id = client.post("/users", json=USER_B).json()["id"]
    # Cookie now belongs to B; switch back to A by re-authenticating
    client.post("/users/logout")
    client.post("/users", json=USER_A)
    # A accesses B's feed — forbidden
    assert client.get(f"/feed/{user_b_id}").status_code == 403


def test_user_b_feed_items_invisible_to_user_a(
    client: TestClient, db: Session
) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    # Add a cached item for A
    db.add(FeedItem(
        user_id=user_a_id, title="A's Article", summary="S",
        source="Src", url="u", topic="T",
    ))
    db.commit()
    # Create B and try to access A's feed
    client.post("/users", json=USER_B)
    assert client.get(f"/feed/{user_a_id}").status_code == 403


def test_user_a_cannot_like_user_b_feed_item(
    client: TestClient, db: Session
) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    item = FeedItem(
        user_id=user_a_id, title="T", summary="S", source="Src", url="u", topic="T",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    # Switch to user B
    client.post("/users", json=USER_B)
    assert client.patch(f"/feed/items/{item.id}/like").status_code == 403


def test_user_a_cannot_update_user_b_profile(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    client.post("/users", json=USER_B)  # cookie is now B
    assert client.put(f"/users/{user_a_id}", json=USER_A).status_code == 403


def test_forged_token_for_other_user_blocked_on_feed(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    user_b_id = client.post("/users", json=USER_B).json()["id"]
    # Forge a valid JWT for user A (legitimate) to try to access B's feed
    client.cookies.set("access_token", create_access_token(user_a_id))
    assert client.get(f"/feed/{user_b_id}").status_code == 403


# ---------------------------------------------------------------------------
# Feed cache TTL boundary
# ---------------------------------------------------------------------------


def _insert_item(db: Session, user_id: int, seconds_old: float) -> FeedItem:
    item = FeedItem(
        user_id=user_id, title="Cached", summary="S",
        source="Src", url="u", topic="T",
        fetched_at=datetime.now(timezone.utc) - timedelta(seconds=seconds_old),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_cache_just_under_6h_not_refreshed(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_item(db, user_id, seconds_old=6 * 3600 - 5)  # 5 seconds fresh
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        resp = client.get(f"/feed/{user_id}")
    assert resp.status_code == 200
    mock_gen.assert_not_called()


def test_cache_just_over_6h_triggers_refresh(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_item(db, user_id, seconds_old=6 * 3600 + 5)  # 5 seconds stale
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = [{
            "user_id": user_id, "title": "Fresh", "summary": "S",
            "source": "Src", "url": "u", "topic": "T", "published_date": "2026-01-01",
        }]
        resp = client.get(f"/feed/{user_id}")
    assert resp.status_code == 200
    mock_gen.assert_called_once()


# ---------------------------------------------------------------------------
# Refresh does not accumulate items
# ---------------------------------------------------------------------------


def _feed_payload(user_id: int, count: int = 3) -> list[dict]:
    return [
        {
            "user_id": user_id,
            "title": f"Article {i}",
            "summary": "S",
            "source": "Src",
            "url": f"https://example.com/{i}",
            "topic": "T",
            "published_date": "2026-01-01",
        }
        for i in range(count)
    ]


def test_second_refresh_does_not_double_items(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _feed_payload(user_id, count=5)
        client.post(f"/feed/{user_id}/refresh")
        # Second refresh — reset cooldown so the route allows it, then verify
        # old 5 are deleted and 5 new are stored (no doubling).
        _feed_route._last_refresh.clear()
        mock_gen.return_value = _feed_payload(user_id, count=5)
        resp = client.post(f"/feed/{user_id}/refresh")
    assert resp.status_code == 200
    assert len(resp.json()) == 5  # must not be 10


def test_refresh_after_get_replaces_all_items(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    _insert_item(db, user_id, seconds_old=0)  # 1 cached item
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _feed_payload(user_id, count=3)
        resp = client.post(f"/feed/{user_id}/refresh")
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()]
    assert "Cached" not in titles
    assert len(titles) == 3


# ---------------------------------------------------------------------------
# Liked items are cleared when feed is refreshed (documented behaviour)
# ---------------------------------------------------------------------------


def test_liked_item_disappears_after_refresh(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_item(db, user_id, seconds_old=0)
    item_id = item.id  # capture plain int before any route calls
    # Like the item
    client.patch(f"/feed/items/{item_id}/like")
    liked_item = db.get(FeedItem, item_id)
    assert liked_item is not None and liked_item.liked is True
    # Force refresh — all old items deleted, new ones have liked=False
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _feed_payload(user_id, count=2)
        client.post(f"/feed/{user_id}/refresh")
    # SQLite can reuse the deleted primary key, so we cannot check "id is gone".
    # Instead verify the business invariants:
    #   1. exactly 2 items (from the mock) exist for this user
    #   2. none of them carry the old liked=True state
    db.expire_all()
    new_items = db.query(FeedItem).filter(FeedItem.user_id == user_id).all()
    assert len(new_items) == 2
    assert not any(i.liked for i in new_items)
    # The old liked item's title ("Cached") must not appear in the new feed
    assert not any(i.title == "Cached" for i in new_items)


# ---------------------------------------------------------------------------
# Like toggle — three-step state machine
# ---------------------------------------------------------------------------


def test_like_three_toggles_ends_liked(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    item = _insert_item(db, user_id, seconds_old=0)
    client.patch(f"/feed/items/{item.id}/like")   # False → True
    client.patch(f"/feed/items/{item.id}/like")   # True  → False
    resp = client.patch(f"/feed/items/{item.id}/like")  # False → True
    assert resp.json()["liked"] is True


def test_event_like_three_toggles_ends_liked(client: TestClient, db: Session) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    ev = Event(
        user_id=user_id, name="Conf", date="2026-05-01",
        fetched_at=datetime.now(timezone.utc),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    client.patch(f"/events/items/{ev.id}/like")
    client.patch(f"/events/items/{ev.id}/like")
    resp = client.patch(f"/events/items/{ev.id}/like")
    assert resp.json()["liked"] is True


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------


def test_deleting_user_cascades_to_feed_items(db: Session) -> None:
    user = User(
        name="Temp", occupation="Dev",
        selected_chips=["Python"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.add(FeedItem(
        user_id=user_id, title="T", summary="S", source="Src", url="u", topic="T",
    ))
    db.commit()
    assert db.query(FeedItem).filter_by(user_id=user_id).count() == 1
    # Delete user
    db.delete(db.get(User, user_id))
    db.commit()
    # Feed items must be gone via cascade
    assert db.query(FeedItem).filter_by(user_id=user_id).count() == 0


def test_deleting_user_cascades_to_events(db: Session) -> None:
    user = User(
        name="Temp2", occupation="Dev",
        selected_chips=["NLP"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.add(Event(
        user_id=user_id, name="E", date="2026-01-01",
    ))
    db.commit()
    assert db.query(Event).filter_by(user_id=user_id).count() == 1
    db.delete(db.get(User, user_id))
    db.commit()
    assert db.query(Event).filter_by(user_id=user_id).count() == 0


# ---------------------------------------------------------------------------
# Agent 502 propagation
# ---------------------------------------------------------------------------


def test_get_feed_background_generation_on_api_error(client: TestClient) -> None:
    """GET /feed returns 200 with X-Feed-Generating; errors are logged in background."""
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = ValueError("GEMINI_API_KEY is not set in environment")
        resp = client.get(f"/feed/{user_id}")
    assert resp.status_code == 200
    assert resp.headers.get("X-Feed-Generating") == "true"
    assert resp.json() == []


def test_get_events_background_generation_on_api_error(client: TestClient) -> None:
    """GET /events returns 200 with X-Events-Generating; errors are logged in background."""
    user_id = client.post("/users", json=USER_A).json()["id"]
    with patch("agents.research_agent.generate_events", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = ValueError("GEMINI_API_KEY is not set in environment")
        resp = client.get(f"/events/{user_id}")
    assert resp.status_code == 200
    assert resp.headers.get("X-Events-Generating") == "true"
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Feed ordering guarantee
# ---------------------------------------------------------------------------


def test_feed_returned_in_descending_fetched_at_order(
    client: TestClient, db: Session
) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    now = datetime.now(timezone.utc)
    for i, delta_hours in enumerate([5, 3, 1]):  # oldest first
        db.add(FeedItem(
            user_id=user_id, title=f"Item {i}", summary="S",
            source="Src", url="u", topic="T",
            fetched_at=now - timedelta(hours=delta_hours),
        ))
    db.commit()
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock):
        resp = client.get(f"/feed/{user_id}")
    titles = [i["title"] for i in resp.json()]
    # Most recent (1h old = Item 2) should be first
    assert titles[0] == "Item 2"
    assert titles[-1] == "Item 0"


# ---------------------------------------------------------------------------
# Profile round-trip: create → update → verify
# ---------------------------------------------------------------------------


def test_full_profile_round_trip(client: TestClient) -> None:
    # Create
    resp = client.post("/users", json={
        **USER_A,
        "selected_chips": ["LLMs", "RAG"],
    })
    assert resp.status_code == 200
    user_id = resp.json()["id"]

    # Verify creation
    me = client.get("/users/me").json()
    assert me["selected_chips"] == ["LLMs", "RAG"]

    # Update
    resp2 = client.put(f"/users/{user_id}", json={
        **USER_A,
        "selected_chips": ["Zero Trust", "OSINT", "Malware Analysis"],
    })
    assert resp2.status_code == 200
    updated = resp2.json()
    assert updated["selected_chips"] == ["Zero Trust", "OSINT", "Malware Analysis"]

    # Fetch again to confirm persistence
    me2 = client.get("/users/me").json()
    assert me2["selected_chips"] == ["Zero Trust", "OSINT", "Malware Analysis"]
