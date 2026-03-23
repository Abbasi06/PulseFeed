"""
Tests for agent helper functions.
No real API calls — Gemini and DuckDuckGo are mocked or avoided entirely.
"""
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

from models import User

from agents.research_agent import (
    MAX_EVENTS,
    MAX_FEED,
    _build_event_queries,
    _build_feed_queries,
    _validate_events,
    _validate_feed_items,
    search_web,
)


# ---------------------------------------------------------------------------
# _validate_feed_items
# ---------------------------------------------------------------------------


def test_validate_feed_items_keeps_valid_item() -> None:
    raw: list[dict[str, object]] = [{"title": "Hello", "summary": "World", "source": "S", "url": "u", "topic": "AI"}]
    result = _validate_feed_items(raw, user_id=1)
    assert len(result) == 1
    assert result[0]["title"] == "Hello"


def test_validate_feed_items_discards_both_empty() -> None:
    raw: list[dict[str, object]] = [{"title": "", "summary": "", "source": "S", "url": "u", "topic": "AI"}]
    assert _validate_feed_items(raw, user_id=1) == []


def test_validate_feed_items_discards_when_title_and_summary_none() -> None:
    raw: list[dict[str, object]] = [{"title": None, "summary": None}]
    assert _validate_feed_items(raw, user_id=1) == []


def test_validate_feed_items_keeps_item_with_only_title() -> None:
    raw: list[dict[str, object]] = [{"title": "Title only", "summary": ""}]
    result = _validate_feed_items(raw, user_id=1)
    assert len(result) == 1


def test_validate_feed_items_keeps_item_with_only_summary() -> None:
    raw: list[dict[str, object]] = [{"title": "", "summary": "Summary only"}]
    result = _validate_feed_items(raw, user_id=1)
    assert len(result) == 1


def test_validate_feed_items_applies_title_default() -> None:
    raw: list[dict[str, object]] = [{"title": "", "summary": "Something", "source": "S"}]
    result = _validate_feed_items(raw, user_id=1)
    assert result[0]["title"] == "Untitled"


def test_validate_feed_items_applies_source_default() -> None:
    raw: list[dict[str, object]] = [{"title": "T", "summary": "S", "source": None}]
    result = _validate_feed_items(raw, user_id=1)
    assert result[0]["source"] == "Unknown"


def test_validate_feed_items_applies_url_default() -> None:
    raw: list[dict[str, object]] = [{"title": "T", "summary": "S", "url": None}]
    result = _validate_feed_items(raw, user_id=1)
    assert result[0]["url"] == "#"


def test_validate_feed_items_applies_topic_default() -> None:
    raw: list[dict[str, object]] = [{"title": "T", "summary": "S", "topic": ""}]
    result = _validate_feed_items(raw, user_id=1)
    assert result[0]["topic"] == "General"


def test_validate_feed_items_caps_at_max() -> None:
    raw: list[dict[str, object]] = [{"title": f"T{i}", "summary": "S"} for i in range(MAX_FEED + 5)]
    result = _validate_feed_items(raw, user_id=1)
    assert len(result) == MAX_FEED


def test_validate_feed_items_sets_user_id() -> None:
    raw: list[dict[str, object]] = [{"title": "T", "summary": "S"}]
    result = _validate_feed_items(raw, user_id=99)
    assert result[0]["user_id"] == 99


# ---------------------------------------------------------------------------
# _validate_events
# ---------------------------------------------------------------------------


def test_validate_events_keeps_valid_event() -> None:
    raw: list[dict[str, object]] = [{"name": "PyCon", "date": "2026-05-15", "location": "Pittsburgh"}]
    result = _validate_events(raw, user_id=1)
    assert len(result) == 1
    assert result[0]["name"] == "PyCon"


def test_validate_events_discards_missing_name() -> None:
    raw: list[dict[str, object]] = [{"name": "", "date": "2026-05-15"}]
    assert _validate_events(raw, user_id=1) == []


def test_validate_events_discards_none_name() -> None:
    raw: list[dict[str, object]] = [{"name": None, "date": "2026-05-15"}]
    assert _validate_events(raw, user_id=1) == []


def test_validate_events_discards_missing_date() -> None:
    raw: list[dict[str, object]] = [{"name": "PyCon", "date": ""}]
    assert _validate_events(raw, user_id=1) == []


def test_validate_events_discards_none_date() -> None:
    raw: list[dict[str, object]] = [{"name": "PyCon", "date": None}]
    assert _validate_events(raw, user_id=1) == []


def test_validate_events_defaults_url_to_hash() -> None:
    raw: list[dict[str, object]] = [{"name": "PyCon", "date": "2026-05-15", "url": None}]
    result = _validate_events(raw, user_id=1)
    assert result[0]["url"] == "#"


def test_validate_events_caps_at_max() -> None:
    raw: list[dict[str, object]] = [{"name": f"Event{i}", "date": "2026-01-01"} for i in range(MAX_EVENTS + 5)]
    result = _validate_events(raw, user_id=1)
    assert len(result) == MAX_EVENTS


def test_validate_events_sets_user_id() -> None:
    raw: list[dict[str, object]] = [{"name": "Conf", "date": "2026-01-01"}]
    result = _validate_events(raw, user_id=77)
    assert result[0]["user_id"] == 77


# ---------------------------------------------------------------------------
# _build_feed_queries
# ---------------------------------------------------------------------------


def _user(occupation: str, interests: list[str]) -> User:
    return cast(User, SimpleNamespace(occupation=occupation, interests=interests, hobbies=[]))


def test_build_feed_queries_includes_occupation() -> None:
    queries = _build_feed_queries(_user("Data Scientist", ["ML"]))
    assert any("Data Scientist" in q for q in queries)


def test_build_feed_queries_includes_interests() -> None:
    queries = _build_feed_queries(_user("Engineer", ["AI", "Python", "Rust"]))
    texts = " ".join(queries)
    assert "AI" in texts
    assert "Python" in texts


def test_build_feed_queries_only_uses_first_two_interests() -> None:
    queries = _build_feed_queries(_user("Engineer", ["AI", "Python", "Rust"]))
    texts = " ".join(queries)
    assert "Rust" not in texts


def test_build_feed_queries_returns_list_of_strings() -> None:
    queries = _build_feed_queries(_user("Engineer", ["AI"]))
    assert isinstance(queries, list)
    assert all(isinstance(q, str) for q in queries)


# ---------------------------------------------------------------------------
# _build_event_queries
# ---------------------------------------------------------------------------


def test_build_event_queries_includes_occupation() -> None:
    queries = _build_event_queries(_user("ML Engineer", ["AI"]))
    assert any("ML Engineer" in q for q in queries)


def test_build_event_queries_includes_interests() -> None:
    queries = _build_event_queries(_user("Engineer", ["AI", "Python"]))
    texts = " ".join(queries)
    assert "AI" in texts
    assert "Python" in texts


def test_build_event_queries_only_uses_first_two_interests() -> None:
    queries = _build_event_queries(_user("Engineer", ["AI", "Python", "Rust"]))
    texts = " ".join(queries)
    assert "Rust" not in texts


# ---------------------------------------------------------------------------
# search_web — error resilience
# ---------------------------------------------------------------------------


def test_search_web_returns_empty_list_on_exception() -> None:
    with patch("agents.research_agent.DDGS") as mock_ddgs_cls:
        mock_ddgs_cls.return_value.__enter__.return_value.text.side_effect = (
            RuntimeError("network error")
        )
        result = search_web("test query")
    assert result == []


def test_search_web_returns_empty_list_when_ddgs_returns_none() -> None:
    with patch("agents.research_agent.DDGS") as mock_ddgs_cls:
        mock_ddgs_cls.return_value.__enter__.return_value.text.return_value = None
        result = search_web("test query")
    assert result == []


def test_search_web_passes_timelimit() -> None:
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text.return_value = []
    with patch("agents.research_agent.DDGS", return_value=mock_ddgs):
        search_web("query", timelimit="d")
    mock_ddgs.text.assert_called_once_with("query", max_results=5, timelimit="d")
