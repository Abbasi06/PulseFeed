"""
Tests for src/pipeline/bouncer.py — heuristic pre-filter stage.
No LLM calls; purely tests word-count and spam-title logic.
"""


from src.pipeline.bouncer import MIN_WORDS, run_bouncer
from src.schemas import RawDocument
from tests.conftest import make_raw_doc


def _doc(title: str = "Normal Title About Systems", words: int = 320) -> RawDocument:
    body = " ".join(["word"] * words)
    return RawDocument.model_validate(make_raw_doc(title=title, body=body))


class TestRunBouncer:
    def test_passes_normal_document(self) -> None:
        result = run_bouncer(_doc())
        assert result.passed is True
        assert result.rejection_reason is None
        assert result.word_count >= MIN_WORDS

    def test_rejects_too_short_body(self) -> None:
        short_doc = RawDocument.model_validate(
            make_raw_doc(body=" ".join(["word"] * 99))
        )
        result = run_bouncer(short_doc)
        assert result.passed is False
        assert result.rejection_reason == "too_short"
        assert result.word_count == 99

    def test_passes_at_exactly_min_words(self) -> None:
        doc = RawDocument.model_validate(
            make_raw_doc(body=" ".join(["word"] * MIN_WORDS))
        )
        result = run_bouncer(doc)
        assert result.passed is True

    def test_rejects_spam_title_top_n(self) -> None:
        result = run_bouncer(_doc(title="Top 10 AI Tools for 2025"))
        assert result.passed is False
        assert result.rejection_reason == "spam_title"

    def test_rejects_spam_title_ultimate_guide(self) -> None:
        result = run_bouncer(_doc(title="The Ultimate Guide to Vector Databases"))
        assert result.passed is False
        assert result.rejection_reason == "spam_title"

    def test_rejects_spam_title_step_by_step(self) -> None:
        result = run_bouncer(_doc(title="Step-by-Step Tutorial for LoRA Fine-Tuning"))
        assert result.passed is False
        assert result.rejection_reason == "spam_title"

    def test_rejects_spam_title_complete_roadmap(self) -> None:
        result = run_bouncer(_doc(title="Complete Roadmap for MLOps Engineers"))
        assert result.passed is False
        assert result.rejection_reason == "spam_title"

    def test_word_count_check_before_spam_check(self) -> None:
        """If both failures apply, too_short is reported first."""
        short_spam = RawDocument.model_validate(
            make_raw_doc(
                title="Top 10 AI Tools",
                body=" ".join(["word"] * 50),
            )
        )
        result = run_bouncer(short_spam)
        assert result.rejection_reason == "too_short"

    def test_word_count_recorded_on_pass(self) -> None:
        result = run_bouncer(_doc(words=500))
        assert result.word_count == 500

    def test_word_count_recorded_on_reject(self) -> None:
        doc = RawDocument.model_validate(
            make_raw_doc(body=" ".join(["word"] * 30))
        )
        result = run_bouncer(doc)
        assert result.word_count == 30

    def test_technical_title_passes(self) -> None:
        titles = [
            "Flash Attention 3: Sub-Quadratic Transformer via IO-Aware Algorithm",
            "Efficient GPU Kernel Fusion for Transformer Layers",
            "Distributed Training with Zero-3 Optimizer",
            "vLLM: Easy, Fast, and Cheap LLM Serving with PagedAttention",
        ]
        for title in titles:
            result = run_bouncer(_doc(title=title))
            assert result.passed is True, f"Expected PASS for: {title}"
