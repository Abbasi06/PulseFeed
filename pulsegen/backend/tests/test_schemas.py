"""
Tests for src/schemas.py — Pydantic validation for all pipeline stages.
"""

import pytest
from pydantic import ValidationError

from src.schemas import (
    TAXONOMY_TAGS,
    BouncerResult,
    DataSource,
    ExtractedDocument,
    MetadataGatekeeperResult,
    MomentumSnapshot,
    RawDocument,
    StorageConfirmation,
    StoragePayload,
)
from tests.conftest import make_raw_doc

# ── RawDocument ────────────────────────────────────────────────────────────────


class TestRawDocument:
    def test_valid_document_accepted(self) -> None:
        doc = RawDocument.model_validate(make_raw_doc())
        assert doc.title.startswith("Flash Attention")
        assert doc.source == DataSource.ARXIV

    def test_url_hash_is_sha256_hex(self) -> None:
        doc = RawDocument.model_validate(make_raw_doc(url="https://example.com/abc"))
        assert len(doc.url_hash) == 64
        assert all(c in "0123456789abcdef" for c in doc.url_hash)

    def test_content_hash_differs_from_url_hash(self) -> None:
        doc = RawDocument.model_validate(make_raw_doc())
        assert doc.content_hash != doc.url_hash

    def test_word_count_computed(self) -> None:
        body = "one two three four five"
        doc = RawDocument.model_validate(make_raw_doc(body=body + " word" * 95))
        # At least 100 words required; we passed 100 here
        assert doc.word_count >= 100

    def test_has_spam_title_top_n(self) -> None:
        doc = RawDocument.model_validate(
            make_raw_doc(title="Top 10 AI Tools You Need to Know")
        )
        assert doc.has_spam_title is True

    def test_has_spam_title_ultimate_guide(self) -> None:
        doc = RawDocument.model_validate(
            make_raw_doc(title="The Ultimate Guide to LLM Inference")
        )
        assert doc.has_spam_title is True

    def test_spam_title_false_for_normal_title(self) -> None:
        doc = RawDocument.model_validate(make_raw_doc())
        assert doc.has_spam_title is False

    def test_different_urls_produce_different_hashes(self) -> None:
        doc_a = RawDocument.model_validate(make_raw_doc(url="https://a.com/1"))
        doc_b = RawDocument.model_validate(make_raw_doc(url="https://b.com/2"))
        assert doc_a.url_hash != doc_b.url_hash

    def test_missing_source_raises(self) -> None:
        data = make_raw_doc()
        del data["source"]
        with pytest.raises(ValidationError):
            RawDocument.model_validate(data)

    def test_unknown_source_raises(self) -> None:
        data = make_raw_doc(source="twitter")
        with pytest.raises(ValidationError):
            RawDocument.model_validate(data)

    def test_missing_url_raises(self) -> None:
        data = make_raw_doc()
        del data["url"]
        with pytest.raises(ValidationError):
            RawDocument.model_validate(data)

    def test_author_defaults_to_none(self) -> None:
        doc = RawDocument.model_validate(make_raw_doc())
        assert doc.author is None

    def test_github_source_accepted(self) -> None:
        doc = RawDocument.model_validate(make_raw_doc(source="github"))
        assert doc.source == DataSource.GITHUB

    def test_hackernews_source_accepted(self) -> None:
        doc = RawDocument.model_validate(make_raw_doc(source="hackernews"))
        assert doc.source == DataSource.HACKERNEWS


# ── BouncerResult ──────────────────────────────────────────────────────────────


class TestBouncerResult:
    def test_passed_true(self) -> None:
        r = BouncerResult(passed=True, word_count=350)
        assert r.passed is True
        assert r.rejection_reason is None

    def test_passed_false_with_reason(self) -> None:
        r = BouncerResult(passed=False, word_count=50, rejection_reason="too_short")
        assert r.passed is False
        assert r.rejection_reason == "too_short"


# ── MetadataGatekeeperResult ───────────────────────────────────────────────────


class TestMetadataGatekeeperResult:
    def test_passes_true_when_high_signal_and_high_confidence(self) -> None:
        r = MetadataGatekeeperResult(is_high_signal=True, confidence=0.9)
        assert r.passes is True

    def test_passes_false_when_low_confidence(self) -> None:
        r = MetadataGatekeeperResult(is_high_signal=True, confidence=0.4)
        assert r.passes is False

    def test_passes_false_when_not_high_signal(self) -> None:
        r = MetadataGatekeeperResult(is_high_signal=False, confidence=0.95)
        assert r.passes is False

    def test_confidence_boundary_exactly_06(self) -> None:
        r = MetadataGatekeeperResult(is_high_signal=True, confidence=0.6)
        assert r.passes is True

    def test_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            MetadataGatekeeperResult(is_high_signal=True, confidence=1.5)

    def test_reasoning_optional(self) -> None:
        r = MetadataGatekeeperResult(is_high_signal=True, confidence=0.8)
        assert r.reasoning is None


# ── ExtractedDocument ──────────────────────────────────────────────────────────


class TestExtractedDocument:
    def _valid_payload(self) -> dict:
        return {
            "summary": "This paper presents Flash Attention 3.",
            "bm25_keywords": ["Flash Attention 3", "vLLM", "CUDA", "Triton", "FP8"],
            "taxonomy_tags": ["AI Engineering"],
            "image_url": None,
        }

    def test_valid_document_accepted(self) -> None:
        doc = ExtractedDocument.model_validate(self._valid_payload())
        assert doc.summary.startswith("This paper")
        assert "AI Engineering" in doc.taxonomy_tags

    def test_invalid_taxonomy_tag_raises(self) -> None:
        data = self._valid_payload()
        data["taxonomy_tags"] = ["Cooking Recipes"]
        with pytest.raises(ValidationError):
            ExtractedDocument.model_validate(data)

    def test_too_few_keywords_raises(self) -> None:
        data = self._valid_payload()
        data["bm25_keywords"] = []  # min_length=1 — empty list is invalid
        with pytest.raises(ValidationError):
            ExtractedDocument.model_validate(data)

    def test_too_many_keywords_raises(self) -> None:
        data = self._valid_payload()
        data["bm25_keywords"] = [f"kw{i}" for i in range(11)]
        with pytest.raises(ValidationError):
            ExtractedDocument.model_validate(data)

    def test_all_valid_taxonomy_tags_accepted(self) -> None:
        for tag in TAXONOMY_TAGS:
            data = self._valid_payload()
            data["taxonomy_tags"] = [tag]
            doc = ExtractedDocument.model_validate(data)
            assert tag in doc.taxonomy_tags

    def test_keywords_stripped_of_whitespace(self) -> None:
        data = self._valid_payload()
        data["bm25_keywords"] = ["  Flash Attention  ", " vLLM ", "CUDA", "Triton", "FP8"]
        doc = ExtractedDocument.model_validate(data)
        assert doc.bm25_keywords[0] == "Flash Attention"
        assert doc.bm25_keywords[1] == "vLLM"

    def test_empty_keyword_stripped(self) -> None:
        data = self._valid_payload()
        data["bm25_keywords"] = ["  ", "vLLM", "CUDA", "Triton", "FP8", "NCCL"]
        doc = ExtractedDocument.model_validate(data)
        assert "" not in doc.bm25_keywords
        assert "  " not in doc.bm25_keywords


# ── StoragePayload & StorageConfirmation ───────────────────────────────────────


class TestStoragePayload:
    def test_url_hash_field_present(self) -> None:
        from datetime import UTC, datetime

        payload = StoragePayload(
            source=DataSource.ARXIV,
            url="https://example.com",
            url_hash="abc123",
            content_hash="def456",
            title="Test",
            summary="A summary.",
            bm25_keywords=["kw1", "kw2", "kw3", "kw4", "kw5"],
            taxonomy_tags=["AI Engineering"],
            gatekeeper_confidence=0.85,
            processed_at=datetime.now(UTC),
        )
        assert payload.url_hash == "abc123"

    def test_processed_at_defaults_to_now(self) -> None:
        from datetime import UTC, datetime

        payload = StoragePayload(
            source=DataSource.GITHUB,
            url="https://github.com/test",
            url_hash="hash",
            content_hash="chash",
            title="Repo",
            summary="A summary.",
            bm25_keywords=["kw1", "kw2", "kw3", "kw4", "kw5"],
            taxonomy_tags=["MLOps"],
            gatekeeper_confidence=0.7,
        )
        # Should have been set automatically
        assert payload.processed_at is not None
        delta = datetime.now(UTC) - payload.processed_at.replace(tzinfo=UTC)
        assert abs(delta.total_seconds()) < 5


class TestStorageConfirmation:
    def test_success(self) -> None:
        c = StorageConfirmation(success=True, document_id="uuid-123")
        assert c.success is True
        assert c.document_id == "uuid-123"

    def test_failure(self) -> None:
        c = StorageConfirmation(success=False, error="DB timeout")
        assert c.success is False
        assert c.error == "DB timeout"


# ── MomentumSnapshot ───────────────────────────────────────────────────────────


class TestMomentumSnapshot:
    def test_is_hot_when_velocity_above_threshold(self) -> None:
        snap = MomentumSnapshot(
            tag="AI Engineering",
            count_this_cycle=5,
            baseline_count=2.0,
            velocity=2.5,
        )
        assert snap.is_hot is True

    def test_not_hot_when_velocity_below_threshold(self) -> None:
        snap = MomentumSnapshot(
            tag="AI Engineering",
            count_this_cycle=5,
            baseline_count=4.0,
            velocity=1.25,
        )
        assert snap.is_hot is False

    def test_not_hot_when_count_too_low(self) -> None:
        snap = MomentumSnapshot(
            tag="AI Engineering",
            count_this_cycle=2,
            baseline_count=1.0,
            velocity=2.0,
        )
        # velocity ≥ 1.5 but count < 3 → not hot
        assert snap.is_hot is False

    def test_hot_boundary_exactly_three_count(self) -> None:
        snap = MomentumSnapshot(
            tag="MLOps",
            count_this_cycle=3,
            baseline_count=1.0,
            velocity=3.0,
        )
        assert snap.is_hot is True
