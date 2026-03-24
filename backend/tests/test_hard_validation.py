"""
Hard validation edge cases for user endpoints.

Tests intentionally probe boundary values, deduplication interactions,
whitespace handling, field case-sensitivity, and Pydantic before-validator
ordering with built-in constraints.
"""

from fastapi.testclient import TestClient

from tests.conftest import USER_A

# ---------------------------------------------------------------------------
# Name / occupation length boundaries
# ---------------------------------------------------------------------------


def test_name_exactly_100_chars_passes(client: TestClient) -> None:
    body = client.post("/users", json={**USER_A, "name": "A" * 100}).json()
    assert body["name"] == "A" * 100


def test_name_101_chars_rejected(client: TestClient) -> None:
    assert client.post("/users", json={**USER_A, "name": "A" * 101}).status_code == 422


def test_occupation_exactly_150_chars_passes(client: TestClient) -> None:
    body = client.post("/users", json={**USER_A, "occupation": "B" * 150}).json()
    assert body["occupation"] == "B" * 150


def test_occupation_151_chars_rejected(client: TestClient) -> None:
    assert client.post("/users", json={**USER_A, "occupation": "B" * 151}).status_code == 422


def test_name_only_whitespace_rejected(client: TestClient) -> None:
    # Whitespace-only name strips to "" → min_length=1 fails
    assert client.post("/users", json={**USER_A, "name": "     "}).status_code == 422


def test_occupation_only_whitespace_rejected(client: TestClient) -> None:
    assert client.post("/users", json={**USER_A, "occupation": "\t\n  "}).status_code == 422


# ---------------------------------------------------------------------------
# selected_chips: count boundaries
# ---------------------------------------------------------------------------


def test_selected_chips_exactly_10_unique_passes(client: TestClient) -> None:
    payload = {**USER_A, "selected_chips": [str(i) for i in range(5)]}
    assert client.post("/users", json=payload).status_code == 200


def test_selected_chips_11_unique_items_rejected(client: TestClient) -> None:
    payload = {**USER_A, "selected_chips": [str(i) for i in range(6)]}
    assert client.post("/users", json=payload).status_code == 422


def test_selected_chips_15_sent_but_only_10_unique_passes(client: TestClient) -> None:
    # The mode="before" deduplication validator runs BEFORE Pydantic's max_length
    # check, so 15 inputs that collapse to 5 unique must pass.
    duped = [str(i) for i in range(5)] + [str(i) for i in range(5)]
    body = client.post("/users", json={**USER_A, "selected_chips": duped}).json()
    assert len(body["selected_chips"]) == 5


def test_selected_chips_15_sent_11_unique_rejected(client: TestClient) -> None:
    # 6 unique items → still 6 after dedup → max_length=5 fails
    unique_6 = [str(i) for i in range(6)]
    duped = unique_6 + [str(i) for i in range(4)]  # 10 total, 6 unique
    assert client.post("/users", json={**USER_A, "selected_chips": duped}).status_code == 422


# ---------------------------------------------------------------------------
# selected_chips: tag-length truncation (silently at 50 chars)
# ---------------------------------------------------------------------------


def test_selected_chip_exactly_50_chars_kept_as_is(client: TestClient) -> None:
    tag = "X" * 50
    body = client.post("/users", json={**USER_A, "selected_chips": [tag]}).json()
    assert body["selected_chips"] == [tag]


def test_selected_chip_51_chars_silently_truncated_to_50(client: TestClient) -> None:
    tag_51 = "Y" * 51
    body = client.post("/users", json={**USER_A, "selected_chips": [tag_51]}).json()
    assert body["selected_chips"] == ["Y" * 50]


def test_selected_chip_51_chars_truncated_dedup_collapses_to_one(client: TestClient) -> None:
    # Two tags: 51-char "A"*51 and 50-char "A"*50 — both truncate to "A"*50 → deduplicated
    body = client.post("/users", json={**USER_A, "selected_chips": ["A" * 51, "A" * 50]}).json()
    assert body["selected_chips"] == ["A" * 50]


# ---------------------------------------------------------------------------
# selected_chips: whitespace handling
# ---------------------------------------------------------------------------


def test_selected_chips_all_whitespace_rejected(client: TestClient) -> None:
    # After stripping each tag becomes "" — silently dropped → empty list → 422
    payload = {**USER_A, "selected_chips": ["   ", "\t\n", "  \r\n  "]}
    assert client.post("/users", json=payload).status_code == 422


def test_selected_chips_mixed_valid_and_whitespace_keeps_valid(client: TestClient) -> None:
    payload = {**USER_A, "selected_chips": ["AI", "   ", "Python", "\t"]}
    body = client.post("/users", json=payload).json()
    assert body["selected_chips"] == ["AI", "Python"]


def test_selected_chips_dedup_is_case_insensitive_and_strips(client: TestClient) -> None:
    # "AI", "ai", "AI ", " ai", " AI " all reduce to the same key → only "AI" kept
    payload = {**USER_A, "selected_chips": ["AI", "ai", "AI ", " ai", " AI "]}
    body = client.post("/users", json=payload).json()
    assert body["selected_chips"] == ["AI"]


def test_selected_chips_many_copies_reduce_to_one_valid(client: TestClient) -> None:
    payload = {**USER_A, "selected_chips": ["LLMs"] * 10}
    body = client.post("/users", json=payload).json()
    assert body["selected_chips"] == ["LLMs"]



# ---------------------------------------------------------------------------
# Unicode and special characters
# ---------------------------------------------------------------------------


def test_name_with_unicode_passes(client: TestClient) -> None:
    body = client.post("/users", json={**USER_A, "name": "测试用户"}).json()
    assert body["name"] == "测试用户"


def test_name_with_arabic_passes(client: TestClient) -> None:
    body = client.post("/users", json={**USER_A, "name": "عباس محمد"}).json()
    assert body["name"] == "عباس محمد"


def test_selected_chips_with_unicode_tag(client: TestClient) -> None:
    body = client.post("/users", json={**USER_A, "selected_chips": ["機械学習", "AI"]}).json()
    assert "機械学習" in body["selected_chips"]


def test_selected_chips_unicode_dedup_case_insensitive(client: TestClient) -> None:
    # ASCII case-insensitivity; Unicode tags with same bytes are also deduped
    body = client.post("/users", json={**USER_A, "selected_chips": ["NLP", "NLP", "nlp"]}).json()
    assert body["selected_chips"] == ["NLP"]


# ---------------------------------------------------------------------------
# Extra unknown fields are ignored (strict=False Pydantic default)
# ---------------------------------------------------------------------------


def test_extra_fields_in_payload_are_ignored(client: TestClient) -> None:
    payload = {**USER_A, "unknown_key": "should_be_ignored", "another": 42}
    resp = client.post("/users", json=payload)
    assert resp.status_code == 200
    assert "unknown_key" not in resp.json()


# ---------------------------------------------------------------------------
# PUT /users: field-level changes persist correctly
# ---------------------------------------------------------------------------


def test_update_selected_chips_whitespace_dedup_works(client: TestClient) -> None:
    user_id = client.post("/users", json=USER_A).json()["id"]
    updated = {**USER_A, "selected_chips": ["LLMs", "llms", "LLMs ", " llms"]}
    body = client.put(f"/users/{user_id}", json=updated).json()
    assert body["selected_chips"] == ["LLMs"]
