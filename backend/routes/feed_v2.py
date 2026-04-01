"""
Feed v2 Routes — Two-Stage Recommender API
-------------------------------------------
Exposes the Hybrid Retriever + RL Validator pipeline as HTTP endpoints.
The existing /feed routes (DuckDuckGo-based) are untouched.

Endpoints
---------
POST /v2/feed/generate/{user_id}   — trigger full retrieval + validation + cache
GET  /v2/feed/cached/{user_id}     — return cached feed (or 404 if not generated)
POST /v2/feed/interact/{user_id}   — record a user interaction (like/click/skip)
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import User
from recommender.retriever_agent import RetrieverAgent
from recommender.validator_node import ValidatorNode
from recommender.schemas import (
    FeedCachePayload,
    UserProfile,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v2/feed", tags=["feed-v2"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateResponse(BaseModel):
    user_id: int
    items_count: int
    cached: bool = True


class InteractRequest(BaseModel):
    document_id: int
    action: Literal["like", "click", "skip", "read_complete"]


class InteractResponse(BaseModel):
    recorded: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_profile(user: User) -> UserProfile:
    """Build a UserProfile from the ORM User model."""
    subfields: list[str] = list(user.sub_fields or []) + list(user.selected_chips or [])
    return UserProfile(
        user_id=user.id,
        field=user.field or user.occupation,
        subfields=list(dict.fromkeys(subfields))[:10],   # deduplicate, cap at 10
        recent_search_history=[],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/generate/{user_id}", response_model=GenerateResponse)
def generate_feed(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> GenerateResponse:
    """Run the full Retriever → Validator pipeline and cache the result."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot generate feed for another user")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    profile = _user_profile(user)
    logger.info("Generating v2 feed for user_id=%d field=%r", user_id, profile.field)

    try:
        # Stage 1 — Hybrid retrieval
        retriever = RetrieverAgent()
        candidates = retriever.retrieve(profile)

        # Stage 2 — Validation + personalisation
        validator = ValidatorNode()
        feedback = validator.get_feedback(user_id)
        payload = validator.validate(candidates, feedback, user_id)
        validator.cache_feed(payload)

        return GenerateResponse(user_id=user_id, items_count=len(payload.items))
    except Exception as exc:
        logger.error("v2 feed generation failed for user_id=%d: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Feed generation failed") from exc


@router.get("/cached/{user_id}", response_model=FeedCachePayload)
def get_cached_feed(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> FeedCachePayload:
    """Return the cached v2 feed for the authenticated user."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot read another user's feed")

    payload = ValidatorNode.get_cached_feed(user_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="No cached feed found. Call POST /v2/feed/generate/{user_id} first.",
        )
    return payload


@router.post("/interact/{user_id}", response_model=InteractResponse)
def record_interaction(
    user_id: int,
    body: InteractRequest,
    current_user_id: int = Depends(get_current_user_id),
) -> InteractResponse:
    """Record a user interaction to improve future RL scoring."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot record interaction for another user")

    try:
        import os
        import sys

        from recommender.mcp_client import MCPClient

        cmd = [sys.executable, "-m", "mcp_servers.pg_search_server"]
        with MCPClient(cmd, {**os.environ}) as pg:
            pg.call("record_interaction", {
                "user_id":     user_id,
                "document_id": body.document_id,
                "action":      body.action,
            })
        return InteractResponse(recorded=True)
    except Exception as exc:
        logger.error("Interaction recording failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to record interaction") from exc
