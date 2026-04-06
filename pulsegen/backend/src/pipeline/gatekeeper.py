"""
Stage 3 (LLM): Metadata Gatekeeper — single LLM call that classifies whether a
document is high-signal for senior AI/ML engineers.
"""

from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from src.retry import with_backoff
from src.schemas import MetadataGatekeeperResult, _GatekeeperLLMResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a signal quality filter for a technical knowledge pipeline
targeting senior AI/ML engineers and infrastructure specialists.

HIGH SIGNAL — include if it is:
- Original research (new algorithms, benchmarks, ablation studies)
- System design deep-dives (architecture decisions, trade-offs, post-mortems)
- Engineering reports with metrics (latency numbers, throughput, cost analysis)
- Infrastructure deep-dives (Kubernetes, distributed training, GPU optimization)
- Security research with technical depth (CVE analysis, zero-trust implementation)
- LLM/ML tooling releases with technical substance
- Agentic systems with novel architectures

LOW SIGNAL — reject if it is:
- Beginner tutorials or "how to get started" guides
- Generic opinion pieces without technical substance
- Job postings, company announcements, press releases
- "Top N tools/frameworks" listicles
- Rephrased summaries of other articles without original analysis
- Marketing content for products

Respond with valid JSON only:
{"is_high_signal": <bool>, "confidence": <float 0.0-1.0>, "reasoning": "<one concise sentence>"}
"""


@with_backoff(max_retries=3, base_delay=2.0, exceptions=(Exception,))
async def run_gatekeeper(
    client: AsyncOpenAI,
    model: str,
    doc_title: str,
    doc_author: str | None,
    doc_source: str,
    doc_body_prefix: str,
) -> MetadataGatekeeperResult:
    """
    Send a single LLM call to evaluate document signal quality.

    Args:
        client:          Configured openai.AsyncOpenAI instance (pointed at llama.cpp light server).
        model:           Model ID (e.g. "gemma3-1b" — fast binary classification).
        doc_title:       Document title.
        doc_author:      Author string or None.
        doc_source:      Source name / DataSource value.
        doc_body_prefix: First 600 characters of the document body.

    Returns:
        MetadataGatekeeperResult with is_high_signal, confidence, and reasoning.
        On JSON parse failure returns a safe default with confidence=0.0.

    Raises:
        Exception on network / API failure (after retries exhausted), so the
        Celery task can decide whether to retry the whole pipeline step.
    """
    author_line = f"Author: {doc_author}" if doc_author else "Author: unknown"
    user_message = (
        f"Title: {doc_title}\n"
        f"{author_line}\n"
        f"Source: {doc_source}\n\n"
        f"Body excerpt:\n{doc_body_prefix[:600]}"
    )

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw_text: str = response.choices[0].message.content or ""

    try:
        parsed = _GatekeeperLLMResponse.model_validate(json.loads(raw_text))
        result = MetadataGatekeeperResult(
            is_high_signal=parsed.is_high_signal,
            confidence=parsed.confidence,
            reasoning=parsed.reasoning,
        )
        logger.debug(
            "Gatekeeper '%s': high_signal=%s confidence=%.2f reasoning=%s",
            doc_title,
            result.is_high_signal,
            result.confidence,
            result.reasoning,
        )
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(
            "Gatekeeper parse_error for '%s': %s — raw=%r",
            doc_title,
            exc,
            raw_text[:200],
        )
        return MetadataGatekeeperResult(
            is_high_signal=False,
            confidence=0.0,
            reasoning="parse_error",
        )
