"""
Hard edge-case tests for agent helpers.

Covers _parse_json_list (new), _validate_feed_items, _validate_events,
_build_feed_queries, and _build_event_queries with adversarial inputs:
malformed Gemini output, boundary item counts, whitespace-only fields,
and all-format query generation.
"""

from types import SimpleNamespace
from typing import cast


from models import User
from agents.research_agent import (
    MAX_EVENTS,
    MAX_FEED,
    _build_event_queries,
    _build_feed_queries,
    _parse_json_list,
    _parse_json_object,
    _validate_brief,
    _validate_events,
    _validate_feed_items,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _user(
    occupation: str = "Engineer",
    selected_chips: list[str] | None = None,
) -> User:
    return cast(
        User,
        SimpleNamespace(
            occupation=occupation,
            selected_chips=selected_chips or [],
        ),
    )


# ---------------------------------------------------------------------------
# _parse_json_list — Gemini output resilience
# ---------------------------------------------------------------------------


def test_parse_json_empty_string_returns_empty() -> None:
    assert _parse_json_list("", "ctx") == []


def test_parse_json_null_literal_returns_empty() -> None:
    assert _parse_json_list("null", "ctx") == []


def test_parse_json_boolean_true_returns_empty() -> None:
    assert _parse_json_list("true", "ctx") == []


def test_parse_json_plain_object_returns_empty() -> None:
    assert _parse_json_list('{"key": "value"}', "ctx") == []


def test_parse_json_number_returns_empty() -> None:
    assert _parse_json_list("42", "ctx") == []


def test_parse_json_truncated_returns_empty() -> None:
    # Gemini output cut off mid-stream
    assert _parse_json_list('[{"title": "T"', "ctx") == []


def test_parse_json_valid_array_returned() -> None:
    result = _parse_json_list('[{"title": "T", "summary": "S"}]', "ctx")
    assert result == [{"title": "T", "summary": "S"}]


def test_parse_json_empty_array_returned() -> None:
    assert _parse_json_list("[]", "ctx") == []


def test_parse_json_whitespace_padded_array() -> None:
    result = _parse_json_list('  \n\n  [{"a": 1}]  \n  ', "ctx")
    assert result == [{"a": 1}]


def test_parse_json_fenced_with_json_language_tag() -> None:
    fenced = '```json\n[{"title": "T"}]\n```'
    result = _parse_json_list(fenced, "ctx")
    assert result == [{"title": "T"}]


def test_parse_json_fenced_without_language_tag() -> None:
    fenced = '```\n[{"title": "T"}]\n```'
    result = _parse_json_list(fenced, "ctx")
    assert result == [{"title": "T"}]


def test_parse_json_fenced_empty_array() -> None:
    assert _parse_json_list("```json\n[]\n```", "ctx") == []


def test_parse_json_fenced_multiline_objects() -> None:
    fenced = '```json\n[\n  {"title": "A"},\n  {"title": "B"}\n]\n```'
    result = _parse_json_list(fenced, "ctx")
    assert len(result) == 2
    assert result[0]["title"] == "A"
    assert result[1]["title"] == "B"


def test_parse_json_garbage_inside_fences_returns_empty() -> None:
    fenced = "```json\nnot valid json at all\n```"
    assert _parse_json_list(fenced, "ctx") == []


def test_parse_json_array_of_non_dicts_is_still_returned() -> None:
    # We only check it's a list; individual item types are validated later
    result = _parse_json_list('[1, 2, 3]', "ctx")
    assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# _validate_feed_items — adversarial inputs
# ---------------------------------------------------------------------------


def test_validate_feed_items_whitespace_title_uses_default() -> None:
    # "   ".strip() == "" → treated as empty → default "Untitled" applied
    raw: list[dict[str, object]] = [{"title": "   ", "summary": "Real content"}]
    result = _validate_feed_items(raw, user_id=1)
    assert result[0]["title"] == "Untitled"
    assert result[0]["summary"] == "Real content"


def test_validate_feed_items_whitespace_summary_is_stripped() -> None:
    raw: list[dict[str, object]] = [{"title": "Valid Title", "summary": "   "}]
    result = _validate_feed_items(raw, user_id=1)
    # summary stripped to "" but title is present → item kept
    assert len(result) == 1
    assert result[0]["summary"] == ""


def test_validate_feed_items_both_whitespace_discarded() -> None:
    raw: list[dict[str, object]] = [{"title": "   ", "summary": "\t\n  "}]
    assert _validate_feed_items(raw, user_id=1) == []


def test_validate_feed_items_all_fields_missing_uses_all_defaults() -> None:
    raw: list[dict[str, object]] = [{"title": "T"}]  # only title present
    result = _validate_feed_items(raw, user_id=5)
    item = result[0]
    assert item["source"] == "Unknown"
    assert item["url"] == "#"
    assert item["topic"] == "General"
    assert item["user_id"] == 5


def test_validate_feed_items_user_id_in_raw_is_overwritten(  # IDOR guard
) -> None:
    raw: list[dict[str, object]] = [{"title": "T", "summary": "S", "user_id": 9999}]
    result = _validate_feed_items(raw, user_id=42)
    assert result[0]["user_id"] == 42  # must use passed user_id, not raw value


def test_validate_feed_items_exactly_max_feed_items_all_kept() -> None:
    raw: list[dict[str, object]] = [{"title": f"T{i}", "summary": "S"} for i in range(MAX_FEED)]
    assert len(_validate_feed_items(raw, user_id=1)) == MAX_FEED


def test_validate_feed_items_one_over_max_is_capped() -> None:
    raw: list[dict[str, object]] = [{"title": f"T{i}", "summary": "S"} for i in range(MAX_FEED + 1)]
    assert len(_validate_feed_items(raw, user_id=1)) == MAX_FEED


def test_validate_feed_items_mixed_valid_and_empty_capped_correctly() -> None:
    # 15 valid + 10 empty (discarded) + 5 more valid = 20 valid, capped at MAX_FEED(20)
    valid: list[dict[str, object]] = [{"title": f"T{i}", "summary": "S"} for i in range(25)]
    empty: list[dict[str, object]] = [{"title": "", "summary": ""} for _ in range(10)]
    raw = valid + empty
    result = _validate_feed_items(raw, user_id=1)
    assert len(result) == MAX_FEED


def test_validate_feed_items_zero_length_string_url_uses_default() -> None:
    raw: list[dict[str, object]] = [{"title": "T", "summary": "S", "url": ""}]
    result = _validate_feed_items(raw, user_id=1)
    assert result[0]["url"] == "#"


def test_validate_feed_items_false_value_url_uses_default() -> None:
    raw: list[dict[str, object]] = [{"title": "T", "summary": "S", "url": False}]
    result = _validate_feed_items(raw, user_id=1)
    assert result[0]["url"] == "#"


# ---------------------------------------------------------------------------
# _validate_events — adversarial inputs
# ---------------------------------------------------------------------------


def test_validate_events_all_optional_fields_absent() -> None:
    raw: list[dict[str, object]] = [{"name": "PyCon", "date": "2026-05-15"}]
    result = _validate_events(raw, user_id=1)
    assert result[0]["location"] == ""
    assert result[0]["type"] == ""
    assert result[0]["url"] == "#"
    assert result[0]["reason"] == ""


def test_validate_events_user_id_in_raw_overwritten() -> None:
    raw: list[dict[str, object]] = [{"name": "Conf", "date": "2026-01-01", "user_id": 8888}]
    result = _validate_events(raw, user_id=7)
    assert result[0]["user_id"] == 7


def test_validate_events_exactly_max_events_all_kept() -> None:
    raw: list[dict[str, object]] = [{"name": f"E{i}", "date": "2026-01-01"} for i in range(MAX_EVENTS)]
    assert len(_validate_events(raw, user_id=1)) == MAX_EVENTS


def test_validate_events_one_over_max_capped() -> None:
    raw: list[dict[str, object]] = [{"name": f"E{i}", "date": "2026-01-01"} for i in range(MAX_EVENTS + 1)]
    assert len(_validate_events(raw, user_id=1)) == MAX_EVENTS


def test_validate_events_mixed_valid_and_invalid_capped() -> None:
    valid: list[dict[str, object]] = [{"name": f"E{i}", "date": "2026-01-01"} for i in range(12)]
    invalid: list[dict[str, object]] = [{"name": "", "date": "2026-01-01"} for _ in range(5)]
    raw = valid + invalid
    result = _validate_events(raw, user_id=1)
    assert len(result) == MAX_EVENTS  # capped at 10


def test_validate_events_zero_url_uses_default() -> None:
    raw: list[dict[str, object]] = [{"name": "Conf", "date": "2026-01-01", "url": ""}]
    result = _validate_events(raw, user_id=1)
    assert result[0]["url"] == "#"


# ---------------------------------------------------------------------------
# _build_feed_queries — query count and content
# ---------------------------------------------------------------------------


def test_build_feed_queries_base_plus_three_chips() -> None:
    # base_query + 3 chip queries = 4 total
    user = _user("Engineer", ["AI", "Python", "Rust"])
    assert len(_build_feed_queries(user)) == 4


def test_build_feed_queries_base_plus_one_chip() -> None:
    user = _user("Cybersecurity Engineer", ["OSINT"])
    assert len(_build_feed_queries(user)) == 2  # base + 1 chip


def test_build_feed_queries_occupation_appears_in_base_query() -> None:
    user = _user("Quantum Engineer", ["Qubits"])
    queries = _build_feed_queries(user)
    assert "Quantum Engineer" in queries[0]


# ---------------------------------------------------------------------------
# _build_event_queries — query count and content
# ---------------------------------------------------------------------------


def test_build_event_queries_base_plus_two_chips() -> None:
    user = _user("DevOps Engineer", ["Kubernetes", "Terraform"])
    assert len(_build_event_queries(user)) == 3  # base + 2


def test_build_event_queries_fourth_chip_excluded() -> None:
    user = _user("Machine Learning Engineer", ["LLMs", "Robotics", "NLP", "CV"])
    queries = _build_event_queries(user)
    combined = " ".join(queries)
    assert "LLMs" in combined
    assert "Robotics" in combined
    assert "NLP" in combined
    assert "CV" not in combined  # 4th chip excluded (event queries only use first 3)


def test_build_event_queries_conference_keyword_in_base() -> None:
    user = _user("Software Engineer", ["APIs"])
    base = _build_event_queries(user)[0]
    assert "conference" in base.lower()


def test_build_event_queries_one_chip_yields_two_queries() -> None:
    user = _user("Data Scientist", ["ML"])
    assert len(_build_event_queries(user)) == 2


# ---------------------------------------------------------------------------
# _parse_json_object — Gemini output resilience
# ---------------------------------------------------------------------------


def test_parse_json_object_empty_string_returns_empty() -> None:
    assert _parse_json_object("", "ctx") == {}


def test_parse_json_object_null_returns_empty() -> None:
    assert _parse_json_object("null", "ctx") == {}


def test_parse_json_object_array_returns_empty() -> None:
    assert _parse_json_object('[{"key": "v"}]', "ctx") == {}


def test_parse_json_object_valid_object_returned() -> None:
    result = _parse_json_object('{"headline": "AI takes over"}', "ctx")
    assert result == {"headline": "AI takes over"}


def test_parse_json_object_fenced_with_json_tag() -> None:
    fenced = '```json\n{"headline": "Big day"}\n```'
    assert _parse_json_object(fenced, "ctx") == {"headline": "Big day"}


def test_parse_json_object_fenced_without_tag() -> None:
    fenced = '```\n{"headline": "Big day"}\n```'
    assert _parse_json_object(fenced, "ctx") == {"headline": "Big day"}


def test_parse_json_object_truncated_returns_empty() -> None:
    assert _parse_json_object('{"headline": "trunc', "ctx") == {}


def test_parse_json_object_boolean_returns_empty() -> None:
    assert _parse_json_object("true", "ctx") == {}


# ---------------------------------------------------------------------------
# _validate_brief — adversarial inputs
# ---------------------------------------------------------------------------


def test_validate_brief_user_id_overwritten() -> None:
    raw: dict[str, object] = {
        "user_id": 9999,
        "headline": "H",
        "signals": ["s1"],
        "top_reads": [{"title": "T", "url": "#", "source": "S"}],
        "watch": ["w1"],
    }
    result = _validate_brief(raw, user_id=42)
    assert result["user_id"] == 42


def test_validate_brief_headline_truncated_to_120() -> None:
    raw: dict[str, object] = {"headline": "X" * 150, "signals": [], "top_reads": [], "watch": []}
    result = _validate_brief(raw, user_id=1)
    assert len(result["headline"]) == 120


def test_validate_brief_missing_headline_defaults_to_empty() -> None:
    raw: dict[str, object] = {"signals": ["s1"], "top_reads": [], "watch": []}
    result = _validate_brief(raw, user_id=1)
    assert result["headline"] == ""


def test_validate_brief_signals_capped_at_5() -> None:
    raw: dict[str, object] = {"signals": [f"s{i}" for i in range(10)], "top_reads": [], "watch": []}
    result = _validate_brief(raw, user_id=1)
    assert len(result["signals"]) == 5


def test_validate_brief_watch_capped_at_4() -> None:
    raw: dict[str, object] = {"watch": [f"w{i}" for i in range(8)], "signals": [], "top_reads": []}
    result = _validate_brief(raw, user_id=1)
    assert len(result["watch"]) == 4


def test_validate_brief_top_reads_capped_at_3() -> None:
    reads = [{"title": f"T{i}", "url": "#", "source": "S"} for i in range(6)]
    raw: dict[str, object] = {"top_reads": reads, "signals": [], "watch": []}
    result = _validate_brief(raw, user_id=1)
    assert len(result["top_reads"]) == 3


def test_validate_brief_top_reads_missing_url_defaults_to_hash() -> None:
    raw: dict[str, object] = {
        "top_reads": [{"title": "T", "source": "S"}],
        "signals": [],
        "watch": [],
    }
    result = _validate_brief(raw, user_id=1)
    assert result["top_reads"][0]["url"] == "#"


def test_validate_brief_top_reads_non_dict_items_skipped() -> None:
    raw: dict[str, object] = {
        "top_reads": ["not a dict", {"title": "T", "url": "#", "source": "S"}],
        "signals": [],
        "watch": [],
    }
    result = _validate_brief(raw, user_id=1)
    assert len(result["top_reads"]) == 1


def test_validate_brief_signals_non_list_returns_empty() -> None:
    raw: dict[str, object] = {"signals": "not a list", "top_reads": [], "watch": []}
    result = _validate_brief(raw, user_id=1)
    assert result["signals"] == []


def test_validate_brief_empty_raw_returns_safe_defaults() -> None:
    result = _validate_brief({}, user_id=7)
    assert result["headline"] == ""
    assert result["signals"] == []
    assert result["top_reads"] == []
    assert result["watch"] == []
    assert result["user_id"] == 7
