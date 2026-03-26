from fastapi.testclient import TestClient

from tests.conftest import USER_A, USER_B


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /users — creation & validation
# ---------------------------------------------------------------------------


def test_create_user_success(client: TestClient) -> None:
    resp = client.post("/users", json=USER_A)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Alice"
    assert body["occupation"] == "Software Engineer"
    assert body["selected_chips"] == ["AI", "Python"]
    assert "id" in body



def test_create_user_sets_auth_cookie(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    assert "access_token" in client.cookies


def test_create_user_empty_name_422(client: TestClient) -> None:
    assert client.post("/users", json={**USER_A, "name": ""}).status_code == 422


def test_create_user_whitespace_name_422(client: TestClient) -> None:
    assert client.post("/users", json={**USER_A, "name": "   "}).status_code == 422


def test_create_user_empty_occupation_422(client: TestClient) -> None:
    assert client.post("/users", json={**USER_A, "occupation": ""}).status_code == 422


def test_create_user_no_selected_chips_422(client: TestClient) -> None:
    assert client.post("/users", json={**USER_A, "selected_chips": []}).status_code == 422


def test_create_user_too_many_selected_chips_422(client: TestClient) -> None:
    payload = {**USER_A, "selected_chips": [str(i) for i in range(11)]}
    assert client.post("/users", json=payload).status_code == 422


def test_create_user_strips_whitespace(client: TestClient) -> None:
    payload = {**USER_A, "name": "  Alice  ", "occupation": "  Engineer  "}
    body = client.post("/users", json=payload).json()
    assert body["name"] == "Alice"
    assert body["occupation"] == "Engineer"


def test_create_user_deduplicates_selected_chips(client: TestClient) -> None:
    payload = {**USER_A, "selected_chips": ["AI", "AI", "Python"]}
    body = client.post("/users", json=payload).json()
    assert body["selected_chips"] == ["AI", "Python"]


def test_create_user_deduplicates_selected_chips_case_insensitive(client: TestClient) -> None:
    payload = {**USER_A, "selected_chips": ["AI", "ai", "Ai"]}
    body = client.post("/users", json=payload).json()
    assert body["selected_chips"] == ["AI"]


def test_create_user_trims_tag_whitespace(client: TestClient) -> None:
    payload = {**USER_A, "selected_chips": ["  AI  ", "  Python  "]}
    body = client.post("/users", json=payload).json()
    assert body["selected_chips"] == ["AI", "Python"]


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------


def test_get_me_unauthenticated_401(client: TestClient) -> None:
    assert client.get("/users/me").status_code == 401


def test_get_me_returns_own_profile(client: TestClient) -> None:
    resp = client.post("/users", json=USER_A)
    user_id = resp.json()["id"]
    me = client.get("/users/me").json()
    assert me["id"] == user_id
    assert me["name"] == "Alice"


# ---------------------------------------------------------------------------
# GET /users/{user_id}
# ---------------------------------------------------------------------------


def test_get_user_by_id(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    body = client.get(f"/users/{user_id}").json()
    assert body["id"] == user_id


def test_get_user_not_found_404(client: TestClient) -> None:
    assert client.get("/users/99999").status_code == 404


# ---------------------------------------------------------------------------
# PUT /users/{user_id}
# ---------------------------------------------------------------------------


def test_update_user_success(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    updated = {**USER_A, "name": "Alice Updated"}
    body = client.put(f"/users/{user_id}", json=updated).json()
    assert body["name"] == "Alice Updated"


def test_update_user_forbidden_when_other_user(client: TestClient) -> None:
    user_a_id = client.post("/users", json=USER_A).json()["id"]
    # Create user B — cookie is now for B
    client.post("/users", json=USER_B)
    resp = client.put(f"/users/{user_a_id}", json=USER_A)
    assert resp.status_code == 403


def test_update_user_not_found_404(client: TestClient) -> None:
    from auth import create_access_token
    client.cookies.set("access_token", create_access_token(99999))
    assert client.put("/users/99999", json=USER_A).status_code == 404


# ---------------------------------------------------------------------------
# POST /users/logout
# ---------------------------------------------------------------------------


def test_logout_clears_session(client: TestClient) -> None:
    client.post("/users", json=USER_A)
    assert client.get("/users/me").status_code == 200
    client.post("/users/logout")
    assert client.get("/users/me").status_code == 401
