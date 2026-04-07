"""
Stage 4 (LLM): Extractor — single LLM call that produces a structured summary,
BM25 keywords, taxonomy tags, and image URL from the full document body.
"""

from __future__ import annotations

import json
import logging
from typing import cast

from openai import AsyncOpenAI

from src.retry import with_backoff
from src.schemas import (
    TAXONOMY_TAGS,
    ExtractedDocument,
    TaxonomyTag,
    _ExtractorLLMResponse,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
You are a technical document distiller for senior AI/ML engineers.

Extract structured metadata from the document body.

RULES:
1. summary: Exactly 3 sentences. Dense and technical. Include specific numbers, model names,
   system names where present. Start each sentence with a different grammatical subject.
   No filler phrases like "This paper presents" or "The authors show".

2. bm25_keywords: 5–10 items. ONLY specific named entities:
   - Model names: "Llama-3.1-70B", "Gemini Ultra", "Mistral-7B"
   - Framework names: "vLLM", "SGLang", "Ray Serve", "Triton", "CUDA"
   - Techniques: "Flash Attention 3", "Speculative Decoding", "LoRA", "QLoRA", "RLHF"
   - Protocols/systems: "RDMA", "NCCL", "eBPF", "KEDA", "Envoy"
   BAD examples (too generic): "machine learning", "Python", "AI", "neural network"

3. taxonomy_tags: 1–3 tags. MUST be exact strings from:
   {sorted(TAXONOMY_TAGS)}

4. image_url: Primary image URL from the source article, or null.

Respond with valid JSON only:
{{
  "summary": "...",
  "bm25_keywords": ["...", ...],
  "taxonomy_tags": ["...", ...],
  "image_url": "..." | null
}}
"""

_DEFAULT_TAG: TaxonomyTag = "AI Engineering"


@with_backoff(max_retries=3, base_delay=2.0, exceptions=(Exception,))
async def run_extractor(
    client: AsyncOpenAI,
    model: str,
    body: str,
) -> ExtractedDocument:
    """
    Send a single LLM call to extract structured metadata from a document body.

    Args:
        client: Configured openai.AsyncOpenAI instance (pointed at llama.cpp heavy server).
        model:  Model ID (e.g. "gemma4" — accurate structured JSON extraction).
        body:   Full document body text; only the first 8000 chars are sent.

    Returns:
        ExtractedDocument with summary, bm25_keywords, taxonomy_tags, image_url.
        Invalid taxonomy tags are silently dropped; if all drop, defaults to
        ["AI Engineering"].

    Raises:
        Exception on parse failure or API error (after retries exhausted), so
        the Celery task can decide whether to retry.
    """
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": body[:4000]},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=512,
    )

    raw_text: str = response.choices[0].message.content or ""

    # Let JSON / Pydantic errors propagate so @with_backoff can retry.
    raw_response = _ExtractorLLMResponse.model_validate(json.loads(raw_text))

    # Validate and filter taxonomy tags; fall back to default if none survive.
    valid_tags: list[TaxonomyTag] = [
        cast(TaxonomyTag, tag)
        for tag in raw_response.taxonomy_tags
        if tag in TAXONOMY_TAGS
    ]
    dropped = set(raw_response.taxonomy_tags) - set(valid_tags)
    if dropped:
        logger.warning(
            "Extractor dropped invalid taxonomy tags: %s",
            dropped,
        )
    if not valid_tags:
        logger.warning(
            "Extractor: no valid taxonomy tags after filtering — defaulting to '%s'.",
            _DEFAULT_TAG,
        )
        valid_tags = [_DEFAULT_TAG]

    extracted = ExtractedDocument(
        summary=raw_response.summary,
        bm25_keywords=raw_response.bm25_keywords,
        taxonomy_tags=valid_tags,
        image_url=raw_response.image_url,
    )
    logger.debug(
        "Extractor produced %d keywords, tags=%s",
        len(extracted.bm25_keywords),
        extracted.taxonomy_tags,
    )
    return extracted
