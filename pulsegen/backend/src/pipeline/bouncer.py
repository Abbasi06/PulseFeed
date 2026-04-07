"""
Stage 1 (programmatic): Bouncer — filters documents by word count and spam title.

No LLM calls. Uses computed fields from RawDocument.
"""

from __future__ import annotations

import logging

from src.schemas import BouncerResult, RawDocument

logger = logging.getLogger(__name__)

MIN_WORDS = 100

# Link aggregators (HN) have short bodies by design — lower the bar for them
_SOURCE_MIN_WORDS: dict[str, int] = {
    "hackernews": 30,
}


def run_bouncer(doc: RawDocument) -> BouncerResult:
    """
    Purely programmatic filter. No LLM calls.

    Rejection reasons:
    - "too_short"   — doc.word_count < min threshold (source-specific)
    - "spam_title"  — doc.has_spam_title is True

    Word count check runs first so callers can log meaningful metrics;
    spam check runs second so both reasons are distinguishable.
    """
    min_words = _SOURCE_MIN_WORDS.get(str(doc.source), MIN_WORDS)
    if doc.word_count < min_words:
        logger.warning(
            "Bouncer rejected '%s': too_short (%d words, min=%d)",
            doc.title,
            doc.word_count,
            min_words,
        )
        return BouncerResult(
            passed=False,
            word_count=doc.word_count,
            rejection_reason="too_short",
        )

    if doc.has_spam_title:
        logger.warning(
            "Bouncer rejected '%s': spam_title",
            doc.title,
        )
        return BouncerResult(
            passed=False,
            word_count=doc.word_count,
            rejection_reason="spam_title",
        )

    logger.debug(
        "Bouncer passed '%s' (%d words)",
        doc.title,
        doc.word_count,
    )
    return BouncerResult(
        passed=True,
        word_count=doc.word_count,
        rejection_reason=None,
    )
