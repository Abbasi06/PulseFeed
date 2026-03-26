"""
Trend Analyst Agent
-------------------
Receives raw text scraped from technical sources (ArXiv abstracts, GitHub
READMEs, engineering blog posts, newsletters) and extracts high-signal
technical concepts — exact model names, architectural frameworks, novel
methodologies — that indicate bleeding-edge content.

Usage
-----
    agent = TrendAnalystAgent()
    result = agent.analyze(raw_text)
    for trend in result.extracted_trends:
        print(trend.term, trend.category, trend.context)

This agent is standalone: it makes no MCP tool calls and shares no state
with GeneratorAgent.  It can be called directly, from a Celery task, or
from any other context that has GEMINI_API_KEY in the environment.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time

from google import genai
from google.genai import types
from pydantic import ValidationError

from .prompts import build_trend_analyst_prompt
from .schemas import TrendAnalysisResult

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash-lite"  # separate 20 req/day quota from extractor
_JSON_CONFIG = types.GenerateContentConfig(response_mime_type="application/json")
_MAX_RETRIES = 3


def _extract_retry_delay(err_str: str) -> int:
    match = re.search(r"retry in (\d+)", err_str, re.IGNORECASE)
    return int(match.group(1)) + 5 if match else 65


def _gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _parse_json(text: str) -> dict[str, object]:
    """Strip optional markdown fences and parse JSON from Gemini output."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        inner = parts[1] if len(parts) > 1 else ""
        text = inner.removeprefix("json").strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result  # type: ignore[return-value]
        logger.warning("TrendAnalyst: Gemini returned non-dict JSON")
        return {}
    except json.JSONDecodeError as exc:
        logger.warning("TrendAnalyst: invalid JSON from Gemini: %s", exc)
        return {}


class TrendAnalystAgent:
    """
    Extracts high-signal technical buzzwords from raw text.

    Each call to `analyze()` is stateless — a new Gemini request is made
    every time.  Instantiate once and reuse across multiple texts to share
    the client connection.
    """

    def __init__(self) -> None:
        self._client = _gemini_client()

    def analyze(self, text: str) -> TrendAnalysisResult:
        """
        Process *text* and return a `TrendAnalysisResult`.

        Returns an empty result (zero trends) on LLM or parse failure rather
        than raising, so callers can treat it as a soft error.

        Parameters
        ----------
        text:
            Raw scraped content — any length up to ~12 000 chars is passed
            to the model; longer inputs are silently truncated by the prompt
            builder.
        """
        if not text or not text.strip():
            logger.warning("TrendAnalyst: received empty text — returning empty result")
            return TrendAnalysisResult()

        prompt = build_trend_analyst_prompt(text)

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=_MODEL,
                    contents=prompt,
                    config=_JSON_CONFIG,
                )
                raw = _parse_json(response.text or "")
                return TrendAnalysisResult.model_validate(raw)
            except ValidationError as exc:
                logger.warning("TrendAnalyst: schema validation failed: %s", exc)
                return TrendAnalysisResult()
            except Exception as exc:
                err = str(exc)
                if ("429" in err or "RESOURCE_EXHAUSTED" in err) and attempt < _MAX_RETRIES:
                    delay = _extract_retry_delay(err)
                    logger.warning(
                        "TrendAnalyst: rate limited — retrying in %ds (attempt %d/%d)",
                        delay, attempt + 1, _MAX_RETRIES,
                    )
                    time.sleep(delay)
                else:
                    logger.error("TrendAnalyst: Gemini call failed: %s", exc)
                    return TrendAnalysisResult()
        return TrendAnalysisResult()
