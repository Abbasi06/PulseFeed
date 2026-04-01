"""
Canonical Pydantic schemas for the PulseGen ingestion pipeline.

Pipeline stages:
  Harvest  →  RawDocument
  Bouncer  →  BouncerResult
  Gate     →  MetadataGatekeeperResult
  Extract  →  ExtractedDocument
  Store    →  StoragePayload  →  StorageConfirmation

Swarm / momentum:
  MomentumSnapshot, SourceQualityRecord, AdaptiveQuerySet
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, field_validator

# ─── Taxonomy ─────────────────────────────────────────────────────────────────

TaxonomyTag = Literal[
    "AI Engineering",
    "Agentic Workflows",
    "LLMOps",
    "Distributed Systems",
    "Data Engineering",
    "Cybersecurity/Zero-Trust",
    "GPU Optimization",
    "Edge Computing",
    "MLOps",
]

TAXONOMY_TAGS: frozenset[str] = frozenset(
    [
        "AI Engineering",
        "Agentic Workflows",
        "LLMOps",
        "Distributed Systems",
        "Data Engineering",
        "Cybersecurity/Zero-Trust",
        "GPU Optimization",
        "Edge Computing",
        "MLOps",
    ]
)

# ─── Data Sources ─────────────────────────────────────────────────────────────


class DataSource(str, Enum):
    ARXIV = "arxiv"
    GITHUB = "github"
    HACKERNEWS = "hackernews"
    HUGGINGFACE = "huggingface"
    DEVTO = "devto"
    RSS = "rss"


# ─── Stage 1: Raw Harvest ─────────────────────────────────────────────────────

_SPAM_RE = re.compile(
    r"(?i)"
    r"(top\s*\d+\b"
    r"|ultimate\s+guide"
    r"|beginner.{0,15}course"
    r"|crash\s+course"
    r"|cheat\s+sheet"
    r"|\d+\s+things\s+(you|every)"
    r"|everything\s+you\s+need\s+to\s+know"
    r"|complete\s+roadmap"
    r"|step[- ]by[- ]step\s+tutorial)"
)


class RawDocument(BaseModel):
    title: str
    url: str
    body: str
    author: str | None = None
    published_at: datetime | None = None
    source: DataSource
    source_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @computed_field  # type: ignore[misc]
    @property
    def content_hash(self) -> str:
        payload = self.url + self.body[:1000]
        return hashlib.sha256(payload.encode()).hexdigest()

    @computed_field  # type: ignore[misc]
    @property
    def url_hash(self) -> str:
        return hashlib.sha256(self.url.encode()).hexdigest()

    @computed_field  # type: ignore[misc]
    @property
    def word_count(self) -> int:
        return len(self.body.split())

    @computed_field  # type: ignore[misc]
    @property
    def has_spam_title(self) -> bool:
        return bool(_SPAM_RE.search(self.title))


# ─── Stage 2: Bouncer ────────────────────────────────────────────────────────


class BouncerResult(BaseModel):
    passed: bool
    word_count: int
    rejection_reason: str | None = None  # "too_short" | "spam_title" | None


# ─── Stage 3: Gatekeeper (LLM Step 1) ────────────────────────────────────────


class MetadataGatekeeperResult(BaseModel):
    is_high_signal: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None

    @property
    def passes(self) -> bool:
        return self.is_high_signal and self.confidence >= 0.6


# Raw JSON envelope returned by Gemini for the gatekeeper call
class _GatekeeperLLMResponse(BaseModel):
    is_high_signal: bool
    confidence: float
    reasoning: str | None = None


# ─── Stage 4: Extractor (LLM Step 2) ─────────────────────────────────────────


class ExtractedDocument(BaseModel):
    summary: str = Field(description="Exactly 3 sentences. Dense, technical, specific.")
    bm25_keywords: list[str] = Field(
        min_length=5,
        max_length=10,
        description="Specific named entities: framework names, technique names. Not generic terms.",
    )
    taxonomy_tags: list[TaxonomyTag] = Field(
        min_length=1,
        max_length=3,
    )
    image_url: str | None = None

    @field_validator("taxonomy_tags")
    @classmethod
    def tags_in_taxonomy(cls, v: list[str]) -> list[str]:
        invalid = [t for t in v if t not in TAXONOMY_TAGS]
        if invalid:
            raise ValueError(f"Invalid taxonomy tags: {invalid}")
        return v

    @field_validator("bm25_keywords")
    @classmethod
    def clean_keywords(cls, v: list[str]) -> list[str]:
        return [kw.strip() for kw in v if kw.strip()]


# Raw JSON envelope returned by Gemini for the extractor call
class _ExtractorLLMResponse(BaseModel):
    summary: str
    bm25_keywords: list[str]
    taxonomy_tags: list[str]
    image_url: str | None = None


# ─── Stage 5: Storage ────────────────────────────────────────────────────────


class StoragePayload(BaseModel):
    source: DataSource
    source_id: str | None = None
    url: str
    url_hash: str
    content_hash: str
    title: str
    author: str | None = None
    published_at: datetime | None = None
    summary: str
    bm25_keywords: list[str]
    taxonomy_tags: list[TaxonomyTag]
    image_url: str | None = None
    gatekeeper_confidence: float
    document_id: str | None = None
    embedding_id: str | None = None
    pipeline_status: str = "stored"
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class StorageConfirmation(BaseModel):
    success: bool
    document_id: str | None = None
    error: str | None = None


# ─── Trend Extraction ────────────────────────────────────────────────────────


class TrendCategory(str, Enum):
    HARDWARE = "Hardware"
    ARCHITECTURE = "Architecture"
    METHODOLOGY = "Methodology"
    FRAMEWORK = "Framework"
    MODEL = "Model"


class ExtractedTrend(BaseModel):
    term: str
    category: TrendCategory
    context: str


class TrendAnalysisResult(BaseModel):
    extracted_trends: list[ExtractedTrend]


# ─── Swarm / Momentum ────────────────────────────────────────────────────────


class SourceQualityRecord(BaseModel):
    """Per-source pass rate tracked across cycles for budget allocation."""
    source_id: str
    total_fetched: int = 0
    total_passed_gate: int = 0
    total_stored: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @property
    def pass_rate(self) -> float:
        if self.total_fetched == 0:
            return 0.5  # neutral prior
        return self.total_passed_gate / self.total_fetched


class MomentumSnapshot(BaseModel):
    """Velocity snapshot for a taxonomy tag within a harvest cycle."""
    tag: str
    count_this_cycle: int
    baseline_count: float  # rolling average from previous cycles
    velocity: float  # count_this_cycle / baseline_count; >1.5 = hot

    @property
    def is_hot(self) -> bool:
        return self.velocity >= 1.5 and self.count_this_cycle >= 3


class AdaptiveQuerySet(BaseModel):
    """Output of the query engine for a single source + cycle."""
    source_id: str
    queries: list[str]
    hot_topics: list[str] = Field(default_factory=list)
    base_queries_count: int = 0
    trend_queries_count: int = 0
