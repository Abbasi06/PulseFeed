"""
Tests for src/pipeline/extractor.py — LLM deep-extraction stage.
All Gemini calls are mocked. Validates taxonomy filtering and defaults.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.extractor import _DEFAULT_TAG, run_extractor
from src.schemas import TAXONOMY_TAGS, ExtractedDocument


def _make_client(response_text: str) -> MagicMock:
    """Return a mock AsyncOpenAI client whose chat.completions.create returns response_text."""
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


_VALID_RESPONSE = json.dumps({
    "summary": (
        "Flash Attention 3 reduces memory bandwidth by 3x via tiling. "
        "The algorithm achieves 2.6× speedup on H100 GPUs at BF16 precision. "
        "Token throughput reaches 1.2M tokens/s on a single A100."
    ),
    "bm25_keywords": [
        "Flash Attention 3", "H100", "BF16", "CUDA", "tiling", "memory bandwidth",
    ],
    "taxonomy_tags": ["AI Engineering", "GPU Optimization"],
    "image_url": "https://example.com/fig1.png",
})

_INVALID_TAGS_RESPONSE = json.dumps({
    "summary": "Some paper about cooking.",
    "bm25_keywords": ["chef", "recipe", "spice", "oven", "ingredients", "butter"],
    "taxonomy_tags": ["Cooking", "Food Science"],
    "image_url": None,
})

_MIXED_TAGS_RESPONSE = json.dumps({
    "summary": "A paper mixing valid and invalid taxonomy.",
    "bm25_keywords": ["vLLM", "SGLang", "Ray", "NCCL", "Flash", "LoRA"],
    "taxonomy_tags": ["AI Engineering", "InvalidTag"],
    "image_url": None,
})


class TestRunExtractor:
    async def test_valid_response_parses_correctly(self) -> None:
        client = _make_client(_VALID_RESPONSE)
        with patch("src.pipeline.extractor.with_backoff", lambda **_: lambda f: f):
            result = await run_extractor(client=client, model="gemini-2.0-flash-lite", body="x" * 200)
        assert isinstance(result, ExtractedDocument)
        assert "Flash Attention 3" in result.bm25_keywords
        assert "AI Engineering" in result.taxonomy_tags
        assert result.image_url == "https://example.com/fig1.png"

    async def test_all_invalid_taxonomy_tags_default_to_ai_engineering(self) -> None:
        client = _make_client(_INVALID_TAGS_RESPONSE)
        with patch("src.pipeline.extractor.with_backoff", lambda **_: lambda f: f):
            result = await run_extractor(client=client, model="gemini-2.0-flash-lite", body="x" * 200)
        assert result.taxonomy_tags == [_DEFAULT_TAG]

    def test_default_tag_is_valid_taxonomy_member(self) -> None:
        assert _DEFAULT_TAG in TAXONOMY_TAGS

    async def test_mixed_tags_drops_invalid_keeps_valid(self) -> None:
        client = _make_client(_MIXED_TAGS_RESPONSE)
        with patch("src.pipeline.extractor.with_backoff", lambda **_: lambda f: f):
            result = await run_extractor(client=client, model="gemini-2.0-flash-lite", body="x" * 200)
        assert "AI Engineering" in result.taxonomy_tags
        assert "InvalidTag" not in result.taxonomy_tags

    async def test_body_truncated_to_8000_chars(self) -> None:
        client = _make_client(_VALID_RESPONSE)
        body = "a" * 20_000

        with patch("src.pipeline.extractor.with_backoff", lambda **_: lambda f: f):
            await run_extractor(client=client, model="gemini-2.0-flash-lite", body=body)

        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        assert len(user_content) <= 8000

    async def test_malformed_json_propagates_exception(self) -> None:
        """Extractor lets parse errors propagate so Celery can retry."""
        client = _make_client("not valid json }{")
        with patch("src.pipeline.extractor.with_backoff", lambda **_: lambda f: f):
            with pytest.raises(Exception):
                await run_extractor(client=client, model="gemini-2.0-flash-lite", body="content")

    async def test_image_url_none_when_not_provided(self) -> None:
        response = json.dumps({
            "summary": "Three sentences. One more. And another.",
            "bm25_keywords": ["k1", "k2", "k3", "k4", "k5"],
            "taxonomy_tags": ["MLOps"],
            "image_url": None,
        })
        client = _make_client(response)
        with patch("src.pipeline.extractor.with_backoff", lambda **_: lambda f: f):
            result = await run_extractor(client=client, model="gemini-2.0-flash-lite", body="content")
        assert result.image_url is None

    async def test_all_valid_taxonomy_tags_accepted(self) -> None:
        """Each taxonomy tag in TAXONOMY_TAGS round-trips through the extractor."""
        for tag in TAXONOMY_TAGS:
            response = json.dumps({
                "summary": "Sentence one. Sentence two. Sentence three.",
                "bm25_keywords": ["k1", "k2", "k3", "k4", "k5"],
                "taxonomy_tags": [tag],
                "image_url": None,
            })
            client = _make_client(response)
            with patch("src.pipeline.extractor.with_backoff", lambda **_: lambda f: f):
                result = await run_extractor(client=client, model="test-model", body="body text")
            assert tag in result.taxonomy_tags, f"Tag {tag!r} was not preserved"
