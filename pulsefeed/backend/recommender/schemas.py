from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator


class DataSource(str, Enum):
    ARXIV = "arxiv"
    GITHUB = "github"
    RSS = "rss"


class RawDocument(BaseModel):
    """Phase 1 output: harvested document after heuristic filtering."""

    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1)
    body: str = Field(..., description="Raw full text or abstract")
    author: str = Field(default="Unknown")
    published_at: str = Field(default="", description="ISO 8601 date string")
    source: DataSource

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content_hash(self) -> str:
        digest_input = self.url + self.body[:1000]
        return hashlib.sha256(digest_input.encode()).hexdigest()

    @model_validator(mode="after")
    def enforce_word_count(self) -> RawDocument:
        word_count = len(self.body.split())
        if word_count < 300:
            raise ValueError(f"Body too short ({word_count} words < 300). Discard.")
        return self

    @model_validator(mode="after")
    def enforce_no_spam_title(self) -> RawDocument:
        spam_patterns = [
            r"(?i)^top\s+\d+",
            r"(?i)ultimate\s+guide",
            r"(?i)you\s+won'?t\s+believe",
            r"(?i)best\s+\d+\s+tools",
            r"(?i)complete\s+guide\s+to",
        ]
        for pattern in spam_patterns:
            if re.search(pattern, self.title):
                raise ValueError(f"Title matches spam pattern {pattern!r}. Discard.")
        return self


class MetadataGatekeeperResult(BaseModel):
    """Phase 2 LLM output from gemma4 via llama.cpp."""

    is_high_signal: bool
    confidence: float = Field(..., ge=0.0, le=1.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passes(self) -> bool:
        return self.is_high_signal and self.confidence >= 0.6


TAXONOMY_TAGS: frozenset[str] = frozenset([
    "AI Engineering", "Machine Learning", "Data Analytics",
    "Distributed Systems", "Cloud Infrastructure", "Developer Tooling",
    "Security Engineering", "Database Systems", "API Design",
    "Observability", "Open Source", "Systems Programming",
    "Web Engineering", "Mobile Engineering", "Platform Engineering",
    "Edge Computing",
])


class ExtractedDocument(BaseModel):
    """Phase 3 LLM output from gemma4 via llama.cpp."""

    summary: str = Field(..., min_length=1, max_length=1000)
    bm25_keywords: list[str] = Field(..., min_length=5, max_length=10)
    taxonomy_tags: list[str] = Field(..., min_length=1, max_length=3)
    image_url: str = Field(default="")

    @model_validator(mode="after")
    def validate_taxonomy(self) -> ExtractedDocument:
        invalid = [t for t in self.taxonomy_tags if t not in TAXONOMY_TAGS]
        if invalid:
            raise ValueError(
                f"Invalid taxonomy tags: {invalid}. Must be from: {sorted(TAXONOMY_TAGS)}"
            )
        return self


class StoragePayload(BaseModel):
    """Phase 4 router input — carries provenance + extraction + audit fields."""

    # Provenance (from RawDocument)
    source: DataSource
    source_id: str
    url: str
    title: str
    author: str
    published_at: str
    content_hash: str

    # Extraction results (from ExtractedDocument)
    summary: str
    bm25_keywords: list[str]
    taxonomy_tags: list[str]
    image_url: str

    # Pipeline audit
    gatekeeper_confidence: float
    processed_at: datetime

    # Written by storage router (nullable until filled)
    item_id: int | None = None
    embedding_id: str | None = None
    fts_rowid: int | None = None


# ---------------------------------------------------------------------------
# Trend Analyst schemas
# ---------------------------------------------------------------------------


class TrendCategory(str, Enum):
    HARDWARE = "Hardware"
    ARCHITECTURE = "Architecture"
    METHODOLOGY = "Methodology"
    FRAMEWORK = "Framework"
    MODEL = "Model"


class ExtractedTrend(BaseModel):
    """A single high-signal technical concept extracted from raw text."""

    term: str = Field(..., min_length=1, max_length=120)
    category: TrendCategory
    context: str = Field(..., min_length=1, max_length=300)


class TrendAnalysisResult(BaseModel):
    """Full output of the TrendAnalystAgent for one piece of source text."""

    extracted_trends: list[ExtractedTrend] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Storage Orchestrator schemas
# ---------------------------------------------------------------------------


class FlashTaggerOutput(BaseModel):
    """
    Validated output from the Flash Tagger Agent.
    `trend_density_score` is the canonical field name from that agent;
    the orchestrator maps it to `trend_score` in the database payload.
    """

    summary: str = Field(..., min_length=1, max_length=2000)
    keywords: list[str] = Field(..., min_length=1, max_length=20)
    trend_density_score: float = Field(..., ge=0.0, le=1.0)
    matched_trends: list[str] = Field(default_factory=list)
    image_prompt: str = Field(default="")
    # Optional pre-generated image supplied as base64 string
    image_filename: str | None = None
    image_binary_b64: str | None = None

    @model_validator(mode="after")
    def image_fields_consistent(self) -> FlashTaggerOutput:
        has_name = bool(self.image_filename)
        has_data = bool(self.image_binary_b64)
        if has_name != has_data:
            raise ValueError(
                "image_filename and image_binary_b64 must both be present or both absent"
            )
        return self


class StorageConfirmation(BaseModel):
    """Result returned by StorageOrchestratorAgent after a storage attempt."""

    success: bool
    document_id: int | None = None
    image_local_path: str = ""
    error: str | None = None


# ---------------------------------------------------------------------------
# Two-Stage Recommender schemas
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    """User profile used by the Retriever Agent to construct the search query."""

    user_id: int
    field: str = Field(default="", description="Primary professional field, e.g. 'Data Analytics'")
    subfields: list[str] = Field(default_factory=list, description="Specific focus areas")
    recent_search_history: list[str] = Field(default_factory=list, max_length=20)


class CandidateDocument(BaseModel):
    """One document returned by pg_hybrid_search — input to the Validator Node."""

    id: int
    title: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    trend_score: float = Field(default=0.0, ge=0.0)
    matched_trends: list[str] = Field(default_factory=list)
    image_local_path: str = ""
    final_score: float = Field(default=0.0, ge=0.0)


class UserFeedbackHistory(BaseModel):
    """Aggregated interaction history for one user — feeds the RL reward model."""

    user_id: int
    liked: list[int] = Field(default_factory=list)
    clicked: list[int] = Field(default_factory=list)
    ignored: list[int] = Field(default_factory=list)
    read_complete: list[int] = Field(default_factory=list)


class ValidatedFeedItem(BaseModel):
    """Lightweight, mobile-ready document after Validator Node scoring."""

    id: int
    title: str
    summary: str
    image_url: str = ""
    tags: list[str] = Field(default_factory=list)
    personalization_score: float = Field(default=0.0, ge=0.0, le=1.0)


class FeedCachePayload(BaseModel):
    """Complete cached feed for one user, stored in Redis."""

    user_id: int
    items: list[ValidatedFeedItem] = Field(default_factory=list)
    generated_at: datetime
    ttl_seconds: int = 21_600   # 6 hours — matches existing feed TTL


# ---------------------------------------------------------------------------
# MCP audit schemas
# ---------------------------------------------------------------------------


class MCPToolCall(BaseModel):
    """Audit log model for a single MCP tool invocation."""

    server: str
    tool: str
    arguments: dict[str, Any]
    called_at: datetime


class MCPToolResult(BaseModel):
    """Audit log model for a single MCP tool response."""

    server: str
    tool: str
    result: dict[str, Any]
    error: str | None = None
    duration_ms: float
    returned_at: datetime
