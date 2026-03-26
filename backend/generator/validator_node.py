"""
Validator Node — Stage 2 of the Two-Stage Recommender
------------------------------------------------------
Acts as a zero-shot Reward Model: scores 50 candidate documents against the
user's feedback history, drops items scoring below 0.4, and returns the top
20 as a lightweight mobile-ready payload that gets written to Redis cache.

This is the RL personalisation layer. Once sufficient interaction data exists,
the Gemini scoring call can be replaced with a trained DPO/PPO reward model
without changing the surrounding pipeline.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types as gtypes

from .mcp_client import MCPClient
from .prompts import build_validator_prompt
from .schemas import (
    CandidateDocument,
    FeedCachePayload,
    UserFeedbackHistory,
    ValidatedFeedItem,
)

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 0.4
TOP_N = 20
_VALIDATOR_MODEL = "gemini-2.5-flash"
_JSON_CONFIG = gtypes.GenerateContentConfig(response_mime_type="application/json")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _get_server_cmd(module: str) -> list[str]:
    return [sys.executable, "-m", module]


# ---------------------------------------------------------------------------
# ValidatorNode
# ---------------------------------------------------------------------------


class ValidatorNode:
    """Stage-2 validator: score candidates → filter → rank → cache feed."""

    def __init__(self) -> None:
        self._client = _gemini_client()

    def validate(
        self,
        candidates: list[CandidateDocument],
        feedback: UserFeedbackHistory,
        user_id: int,
    ) -> FeedCachePayload:
        """Score, filter, rank, and cache the feed."""
        scored = self._score_candidates(candidates, feedback)
        filtered = [i for i in scored if i.personalization_score >= SCORE_THRESHOLD]
        filtered.sort(key=lambda x: x.personalization_score, reverse=True)
        top = filtered[:TOP_N]
        return FeedCachePayload(
            user_id=user_id,
            items=top,
            generated_at=datetime.now(tz=timezone.utc),
        )

    def get_feedback(self, user_id: int) -> UserFeedbackHistory:
        """Fetch bucketed interaction history for a user via MCP."""
        env: dict[str, str] = {**os.environ}
        cmd = _get_server_cmd("backend.mcp_servers.pg_search_server")
        with MCPClient(cmd, env) as client:
            result = client.call("get_feedback_history", {"user_id": user_id})
        return UserFeedbackHistory(
            user_id=user_id,
            liked=result.get("liked", []),
            clicked=result.get("clicked", []),
            ignored=result.get("ignored", []),
            read_complete=result.get("read_complete", []),
        )

    def cache_feed(self, payload: FeedCachePayload) -> None:
        """Serialise and store the feed payload in Redis."""
        import redis

        r = redis.Redis.from_url(
            os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        )
        key = f"pulsefeed:feed:v2:{payload.user_id}"
        r.setex(
            key,
            payload.ttl_seconds,
            json.dumps(payload.model_dump(mode="json"), default=str),
        )
        logger.info(
            "Feed cached for user_id=%d (%d items)", payload.user_id, len(payload.items)
        )

    @staticmethod
    def get_cached_feed(user_id: int) -> FeedCachePayload | None:
        """Retrieve a cached feed from Redis; returns None on cache miss."""
        import redis

        r = redis.Redis.from_url(
            os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        )
        key = f"pulsefeed:feed:v2:{user_id}"
        raw = r.get(key)
        if raw is None:
            return None
        return FeedCachePayload(**json.loads(raw))  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score_candidates(
        self,
        candidates: list[CandidateDocument],
        feedback: UserFeedbackHistory,
    ) -> list[ValidatedFeedItem]:
        """Call Gemini to score each candidate; map results to ValidatedFeedItem."""
        candidates_dicts = [c.model_dump() for c in candidates]
        prompt = build_validator_prompt(candidates_dicts, feedback)

        response = self._client.models.generate_content(
            model=_VALIDATOR_MODEL,
            contents=prompt,
            config=_JSON_CONFIG,
        )
        score_lookup = _parse_scores(response.text or "")
        return [_to_feed_item(c, score_lookup) for c in candidates]


# ---------------------------------------------------------------------------
# Private module-level helpers (keep class methods under 40 lines)
# ---------------------------------------------------------------------------


def _parse_scores(raw_text: str) -> dict[int, float]:
    """Parse Gemini's JSON array response into an id→score lookup dict."""
    text = raw_text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        inner = parts[1] if len(parts) > 1 else ""
        text = inner.removeprefix("json").strip()
    try:
        items: list[dict[str, Any]] = json.loads(text)
        return {int(item["id"]): float(item["personalization_score"]) for item in items}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("Failed to parse validator scores: %s", exc)
        return {}


def _to_feed_item(
    c: CandidateDocument, score_lookup: dict[int, float]
) -> ValidatedFeedItem:
    """Map a CandidateDocument + score lookup entry to a ValidatedFeedItem."""
    return ValidatedFeedItem(
        id=c.id,
        title=c.title,
        summary=c.summary,
        image_url=c.image_local_path,
        tags=c.keywords[:5],
        personalization_score=score_lookup.get(c.id, 0.0),
    )
