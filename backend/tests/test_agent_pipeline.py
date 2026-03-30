"""
Tests for agent pipeline logic.
Covers timelimit fallback, Gemini retry, and feed_personalizer fallback.
All external calls (Gemini, DuckDuckGo, generator.db) are mocked.
"""
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from sqlalchemy.orm import Session

from agents.research_agent import (
    _MAX_RETRIES,
    _gemini_call_sync,
    generate_feed,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_search_result(n: int = 5) -> list[dict]:
    return [
        {"title": f"Result {i}", "href": f"https://example.com/{i}", "body": f"Body {i}"}
        for i in range(n)
    ]


def _mock_gemini_response(items: list[dict]) -> MagicMock:
    """Return a mock client whose generate_content returns a JSON array."""
    import json

    mock = MagicMock()
    mock.models.generate_content.return_value.text = json.dumps(items)
    return mock


# ---------------------------------------------------------------------------
# generate_feed — timelimit fallback ("d" → "w")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_feed_uses_day_results_when_sufficient(db: Session) -> None:
    """When timelimit='d' returns >= 5 results, timelimit='w' is never called."""
    db.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO users (name, occupation, field, selected_chips, sub_fields, preferred_formats)"
            " VALUES ('Alice','Engineer','','[\"AI\"]','[]','[]')"
        )
    )
    db.commit()
    user_id_val = db.execute(__import__("sqlalchemy").text("SELECT MAX(id) FROM users")).scalar()

    day_results = _make_search_result(6)
    gemini_items = [{"title": "AI News", "summary": "Summary", "source": "S", "url": "u", "topic": "AI"}]

    with patch("agents.research_agent._get_client", return_value=_mock_gemini_response(gemini_items)), \
         patch("agents.research_agent._search_all") as mock_search_all:
        mock_search_all.return_value = day_results  # 6 results on first call
        await generate_feed(user_id_val, db)

    # _search_all was called exactly once (no week fallback needed)
    mock_search_all.assert_called_once()
    assert mock_search_all.call_args == call(mock_search_all.call_args[0][0], timelimit="d")


@pytest.mark.asyncio
async def test_generate_feed_retries_with_week_when_day_sparse(db: Session) -> None:
    """When timelimit='d' returns < 5 results, timelimit='w' is tried."""
    db.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO users (name, occupation, field, selected_chips, sub_fields, preferred_formats)"
            " VALUES ('Bob','Engineer','','[\"ML\"]','[]','[]')"
        )
    )
    db.commit()
    user_id_val = db.execute(__import__("sqlalchemy").text("SELECT MAX(id) FROM users")).scalar()

    sparse = _make_search_result(3)   # only 3 — triggers fallback
    week_results = _make_search_result(8)
    gemini_items = [{"title": "ML Trends", "summary": "Summary", "source": "S", "url": "u", "topic": "ML"}]

    call_counts: list[str] = []

    def fake_search_all(queries: list, timelimit: str | None = None) -> list:
        call_counts.append(timelimit or "none")
        return sparse if timelimit == "d" else week_results

    with patch("agents.research_agent._get_client", return_value=_mock_gemini_response(gemini_items)), \
         patch("agents.research_agent._search_all", side_effect=fake_search_all):
        await generate_feed(user_id_val, db)

    assert call_counts == ["d", "w"], f"Expected ['d','w'], got {call_counts}"


@pytest.mark.asyncio
async def test_generate_feed_placeholder_when_all_searches_empty(db: Session) -> None:
    """When both 'd' and 'w' return nothing, a placeholder item is returned."""
    db.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO users (name, occupation, field, selected_chips, sub_fields, preferred_formats)"
            " VALUES ('Carol','Designer','','[\"UX\"]','[]','[]')"
        )
    )
    db.commit()
    user_id_val = db.execute(__import__("sqlalchemy").text("SELECT MAX(id) FROM users")).scalar()

    with patch("agents.research_agent._get_client", return_value=MagicMock()), \
         patch("agents.research_agent._search_all", return_value=[]):
        result = await generate_feed(user_id_val, db)

    assert len(result) == 1
    assert result[0]["title"] == "No new updates found"
    assert result[0]["url"] == "#"


# ---------------------------------------------------------------------------
# _gemini_call_sync — retry logic
# ---------------------------------------------------------------------------


def test_gemini_call_sync_retries_on_transient_error() -> None:
    """Transient errors (connection timeout) are retried up to _MAX_RETRIES times."""
    mock_client = MagicMock()
    attempt = 0

    def side_effect(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal attempt
        attempt += 1
        if attempt < 2:
            raise Exception("connection timeout")
        result = MagicMock()
        result.text = "[]"
        return result

    mock_client.models.generate_content.side_effect = side_effect

    with patch("agents.research_agent.time.sleep"):
        result = _gemini_call_sync(mock_client, "test")

    assert result == "[]"
    assert mock_client.models.generate_content.call_count == 2


def test_gemini_call_sync_retries_on_429() -> None:
    """429 / RESOURCE_EXHAUSTED errors trigger retry with extracted delay."""
    mock_client = MagicMock()
    attempt = 0

    def side_effect(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal attempt
        attempt += 1
        if attempt < 2:
            raise Exception("429 RESOURCE_EXHAUSTED retry in 30 seconds")
        result = MagicMock()
        result.text = '["ok"]'
        return result

    mock_client.models.generate_content.side_effect = side_effect

    with patch("agents.research_agent.time.sleep") as mock_sleep:
        result = _gemini_call_sync(mock_client, "test")

    assert result == '["ok"]'
    # Sleep should have been called with extracted delay (30 + 5 = 35)
    mock_sleep.assert_called_once_with(35)


def test_gemini_call_sync_raises_immediately_on_non_retriable_error() -> None:
    """Non-retriable errors (e.g. invalid API key) raise without retrying."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = ValueError("INVALID_ARGUMENT: bad request")

    with patch("agents.research_agent.time.sleep") as mock_sleep:
        with pytest.raises(ValueError, match="INVALID_ARGUMENT"):
            _gemini_call_sync(mock_client, "test")

    mock_sleep.assert_not_called()
    assert mock_client.models.generate_content.call_count == 1


def test_gemini_call_sync_exhausts_retries_and_raises() -> None:
    """After _MAX_RETRIES transient failures the exception propagates."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("503 service_unavailable")

    with patch("agents.research_agent.time.sleep"):
        with pytest.raises(Exception, match="503"):
            _gemini_call_sync(mock_client, "test")

    assert mock_client.models.generate_content.call_count == _MAX_RETRIES + 1


# ---------------------------------------------------------------------------
# feed_personalizer — ImportError / generator.db unavailable → fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_personalize_feed_falls_back_to_research_agent_when_import_fails(
    db: Session,
) -> None:
    """If generator package is missing, personalize_feed calls generate_feed."""
    from agents.feed_personalizer import personalize_feed

    db.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO users (name, occupation, field, selected_chips, sub_fields, preferred_formats)"
            " VALUES ('Dave','Researcher','','[\"NLP\"]','[]','[]')"
        )
    )
    db.commit()
    user_id_val = db.execute(__import__("sqlalchemy").text("SELECT MAX(id) FROM users")).scalar()

    expected = [{"user_id": user_id_val, "title": "NLP Research", "summary": "s",
                 "source": "Arxiv", "url": "u", "topic": "NLP", "published_date": "2026-01-01"}]

    # _open_generator_db is already patched to return None by the autouse fixture
    with patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = expected
        result = await personalize_feed(user_id_val, db)

    mock_gen.assert_called_once_with(user_id_val, db)
    assert result == expected


@pytest.mark.asyncio
async def test_personalize_feed_falls_back_when_fts_results_below_threshold(
    db: Session,
) -> None:
    """If FTS returns fewer than MIN_FTS_RESULTS, generate_feed is called as fallback."""
    from agents.feed_personalizer import MIN_FTS_RESULTS, personalize_feed

    db.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO users (name, occupation, field, selected_chips, sub_fields, preferred_formats)"
            " VALUES ('Eve','Scientist','','[\"Physics\"]','[]','[]')"
        )
    )
    db.commit()
    user_id_val = db.execute(__import__("sqlalchemy").text("SELECT MAX(id) FROM users")).scalar()

    # Simulate a real connection returned by _open_generator_db, but FTS returns sparse rows
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [
        # MIN_FTS_RESULTS - 1 rows (not enough)
    ] * (MIN_FTS_RESULTS - 1)

    expected = [{"user_id": user_id_val, "title": "Physics Update", "summary": "s",
                 "source": "Arxiv", "url": "u", "topic": "Physics", "published_date": "2026-01-01"}]

    with patch("agents.feed_personalizer._open_generator_db", return_value=mock_conn), \
         patch("agents.feed_personalizer._fts_search", return_value=[{"title": "t", "summary": "s"}] * (MIN_FTS_RESULTS - 1)), \
         patch("agents.research_agent.generate_feed", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = expected
        result = await personalize_feed(user_id_val, db)

    mock_gen.assert_called_once_with(user_id_val, db)
    assert result == expected
