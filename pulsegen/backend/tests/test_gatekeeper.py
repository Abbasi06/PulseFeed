"""
Tests for src/pipeline/gatekeeper.py — LLM signal-quality filter.
All Gemini API calls are mocked. No real network I/O.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.gatekeeper import run_gatekeeper
from src.schemas import MetadataGatekeeperResult


def _make_client(response_text: str) -> MagicMock:
    """Return a mock AsyncOpenAI client whose chat.completions.create returns the given text."""
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


_PASS_JSON = json.dumps({
    "is_high_signal": True,
    "confidence": 0.92,
    "reasoning": "Original research with benchmark numbers.",
})

_REJECT_JSON = json.dumps({
    "is_high_signal": False,
    "confidence": 0.15,
    "reasoning": "Beginner tutorial with no original analysis.",
})


class TestRunGatekeeper:
    async def test_high_signal_document_passes(self) -> None:
        client = _make_client(_PASS_JSON)
        with patch("src.pipeline.gatekeeper.with_backoff", lambda **_: lambda f: f):
            result = await run_gatekeeper(
                client=client,
                model="gemini-2.0-flash-lite",
                doc_title="Flash Attention 3: Sub-Quadratic Attention",
                doc_author="Tri Dao",
                doc_source="arxiv",
                doc_body_prefix="We present an I/O-aware implementation...",
            )
        assert isinstance(result, MetadataGatekeeperResult)
        assert result.is_high_signal is True
        assert result.confidence == pytest.approx(0.92)
        assert result.passes is True

    async def test_low_signal_document_rejected(self) -> None:
        client = _make_client(_REJECT_JSON)
        with patch("src.pipeline.gatekeeper.with_backoff", lambda **_: lambda f: f):
            result = await run_gatekeeper(
                client=client,
                model="gemini-2.0-flash-lite",
                doc_title="How to Get Started with Python",
                doc_author=None,
                doc_source="devto",
                doc_body_prefix="In this tutorial we will learn Python basics...",
            )
        assert result.is_high_signal is False
        assert result.passes is False

    async def test_malformed_json_returns_safe_default(self) -> None:
        """Corrupt JSON from Gemini should not raise — return confidence=0.0."""
        client = _make_client("this is not json at all")
        with patch("src.pipeline.gatekeeper.with_backoff", lambda **_: lambda f: f):
            result = await run_gatekeeper(
                client=client,
                model="gemini-2.0-flash-lite",
                doc_title="Test",
                doc_author=None,
                doc_source="rss",
                doc_body_prefix="Some content",
            )
        assert result.is_high_signal is False
        assert result.confidence == 0.0
        assert result.reasoning == "parse_error"

    async def test_empty_response_returns_safe_default(self) -> None:
        client = _make_client("")
        with patch("src.pipeline.gatekeeper.with_backoff", lambda **_: lambda f: f):
            result = await run_gatekeeper(
                client=client,
                model="gemini-2.0-flash-lite",
                doc_title="Test",
                doc_author=None,
                doc_source="hackernews",
                doc_body_prefix="Content",
            )
        assert result.confidence == 0.0
        assert result.passes is False

    async def test_body_prefix_truncated_to_600_chars(self) -> None:
        """Verify only first 600 chars of body_prefix are included in the prompt."""
        client = _make_client(_PASS_JSON)
        long_body = "x" * 2000

        with patch("src.pipeline.gatekeeper.with_backoff", lambda **_: lambda f: f):
            await run_gatekeeper(
                client=client,
                model="gemini-2.0-flash-lite",
                doc_title="Test",
                doc_author="Author",
                doc_source="arxiv",
                doc_body_prefix=long_body,
            )

        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        # The user message should contain at most 600 chars of the body
        assert "x" * 601 not in user_content

    async def test_none_author_handled_gracefully(self) -> None:
        client = _make_client(_PASS_JSON)
        with patch("src.pipeline.gatekeeper.with_backoff", lambda **_: lambda f: f):
            result = await run_gatekeeper(
                client=client,
                model="gemini-2.0-flash-lite",
                doc_title="Test Title",
                doc_author=None,
                doc_source="github",
                doc_body_prefix="Content here",
            )
        assert isinstance(result, MetadataGatekeeperResult)

    async def test_reasoning_field_preserved(self) -> None:
        client = _make_client(_PASS_JSON)
        with patch("src.pipeline.gatekeeper.with_backoff", lambda **_: lambda f: f):
            result = await run_gatekeeper(
                client=client,
                model="gemini-2.0-flash-lite",
                doc_title="Test",
                doc_author=None,
                doc_source="arxiv",
                doc_body_prefix="Content",
            )
        assert result.reasoning == "Original research with benchmark numbers."
