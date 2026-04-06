"""
SwarmCoordinator — central intelligence for the harvest operation.

Each harvest cycle it:
1. Computes MomentumSnapshot for all taxonomy tags (via MomentumTracker)
2. Allocates fetch budget per source (based on SourceQualityRecord pass rates)
3. Generates adaptive query sets per source (via DynamicQueryEngine)
4. After harvest, amplifies cross-source signals (via CrossSourceAmplifier)
5. Updates SourceQualityRecord stats in SQLite

SQLite tables owned by this module:
  source_quality   — per-source gatekeeper pass rate tracking
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

from src.config import settings
from src.schemas import (
    AdaptiveQuerySet,
    RawDocument,
    SourceQualityRecord,
)
from src.swarm.momentum import MomentumTracker
from src.swarm.query_engine import CrossSourceAmplifier, DynamicQueryEngine

logger = logging.getLogger(__name__)

# All registered source IDs — must match CONNECTOR_REGISTRY keys in connectors/__init__.py
ALL_SOURCE_IDS: list[str] = [
    "arxiv",
    "github",
    "hackernews",
    "huggingface",
    "devto",
    "rss",
]

BASE_FETCH_BUDGET: int = 30


class SwarmCoordinator:
    """
    Orchestrates intelligent, adaptive content harvesting across all sources.

    Thread-safety: one instance per Celery worker process.
    SQLite writes use WAL mode; concurrent reads are safe.
    """

    def __init__(self) -> None:
        self._momentum = MomentumTracker()
        self._query_engine = DynamicQueryEngine()
        self._amplifier = CrossSourceAmplifier()
        self._init_db()

    # ── Public API ────────────────────────────────────────────────────────────

    def plan_cycle(
        self, tag_counts_last_cycle: dict[str, int]
    ) -> dict[str, tuple[int, AdaptiveQuerySet]]:
        """
        Returns {source_id: (fetch_budget, AdaptiveQuerySet)} for all sources.

        Algorithm:
        a. Record last-cycle tag counts, compute momentum snapshots
        b. Identify hot tags (velocity ≥ 1.5x, count ≥ 3)
        c. Load amplified cross-source signals from previous cycles
        d. For each source: compute budget + generate adaptive queries
        """
        # Step a: compute snapshots against prior history FIRST, then record this
        # cycle.  record_cycle() writes counts to SQLite; compute_snapshots()
        # calls get_baseline() which reads from that same table.  If we record
        # first, the current cycle's counts contaminate the baseline, driving
        # velocity toward 1.0 and making hot-tag detection insensitive.
        snapshots = self._momentum.compute_snapshots(tag_counts_last_cycle)
        self._momentum.record_cycle(tag_counts_last_cycle)
        hot_tags = [s.tag for s in snapshots if s.is_hot]

        if hot_tags:
            logger.info("Hot topics this cycle: %s", hot_tags)

        # Step b: cross-source signals from prior amplification
        amplified_signals = self._amplifier.load_recent_signals(hours=6)
        if amplified_signals:
            logger.info("Amplified signals available: %s", amplified_signals[:5])

        # Step c: source quality records for budget allocation
        quality_records = self._load_quality_records()

        # Step d: build plan per source
        plan: dict[str, tuple[int, AdaptiveQuerySet]] = {}
        total_budget = 0

        for source_id in ALL_SOURCE_IDS:
            budget = self._compute_budget(
                quality_records.get(source_id), hot_tags
            )
            query_set = self._query_engine.build_queries(
                source_id=source_id,
                hot_tags=hot_tags,
                amplified_signals=amplified_signals,
                max_queries=12,
            )
            plan[source_id] = (budget, query_set)
            total_budget += budget

        logger.info(
            "Cycle plan: %d sources | hot_tags=%s | total_budget=%d | amplified=%d",
            len(plan),
            hot_tags,
            total_budget,
            len(amplified_signals),
        )
        return plan

    def record_harvest_result(
        self,
        source_id: str,
        fetched: int,
        passed_gate: int,
        stored: int,
    ) -> None:
        """
        Atomically increment quality counters for *source_id*.

        Uses INSERT ... ON CONFLICT DO UPDATE with SQL arithmetic so that
        concurrent Celery workers (gevent pool, concurrency=8) never clobber
        each other's increments via a read-modify-write cycle.
        """
        try:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO source_quality
                    (source_id, total_fetched, total_passed_gate, total_stored, last_updated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    total_fetched     = total_fetched     + excluded.total_fetched,
                    total_passed_gate = total_passed_gate + excluded.total_passed_gate,
                    total_stored      = total_stored      + excluded.total_stored,
                    last_updated      = excluded.last_updated
                """,
                (
                    source_id,
                    fetched,
                    passed_gate,
                    stored,
                    datetime.now(tz=UTC).isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("record_harvest_result failed for %s: %s", source_id, exc)

    def post_cycle_amplify(self, harvested_docs: list[RawDocument]) -> list[str]:
        """
        Detect entities mentioned across 2+ different sources in this cycle.
        Persist them for use by the next cycle's query engine.
        Returns the amplified signal list.
        """
        signals = self._amplifier.get_amplified_signals(
            harvested_docs, min_sources=2
        )
        if signals:
            source_counts = self._amplifier.extract_entities(harvested_docs)
            signal_counts = {s: len(source_counts.get(s, [])) for s in signals}
            self._amplifier.persist_signals(signals, signal_counts)
            logger.info(
                "Cross-source amplified: %d signals → %s",
                len(signals),
                signals[:5],
            )
        return signals

    # ── Budget Computation ────────────────────────────────────────────────────

    def _compute_budget(
        self,
        record: SourceQualityRecord | None,
        hot_tags: list[str],
    ) -> int:
        """
        Base budget × quality multiplier × hot-tag bonus.
        Quality multiplier: 0.5 (0% pass rate) → 2.0 (100% pass rate)
        Hot-tag bonus: flat +20% if any hot tags exist
        Clamped: min=10, max=100
        """
        base = BASE_FETCH_BUDGET

        if record is not None and record.total_fetched > 0:
            # pass_rate in [0, 1] → multiplier in [0.5, 2.0]
            multiplier = 0.5 + (record.pass_rate * 1.5)
            base = int(base * multiplier)

        if hot_tags:
            base = int(base * 1.2)

        return min(max(base, 10), 100)

    # ── SQLite Persistence ────────────────────────────────────────────────────

    def _load_quality_records(self) -> dict[str, SourceQualityRecord]:
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT source_id, total_fetched, total_passed_gate, total_stored, last_updated "
                "FROM source_quality"
            ).fetchall()
            conn.close()
        except sqlite3.OperationalError:
            return {}

        records: dict[str, SourceQualityRecord] = {}
        for row in rows:
            try:
                records[row[0]] = SourceQualityRecord(
                    source_id=row[0],
                    total_fetched=row[1],
                    total_passed_gate=row[2],
                    total_stored=row[3],
                    last_updated=datetime.fromisoformat(row[4]),
                )
            except Exception as exc:
                logger.warning("Failed to parse SourceQualityRecord row: %s", exc)
        return records

    def _init_db(self) -> None:
        conn = self._connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS source_quality (
                source_id         TEXT PRIMARY KEY,
                total_fetched     INTEGER NOT NULL DEFAULT 0,
                total_passed_gate INTEGER NOT NULL DEFAULT 0,
                total_stored      INTEGER NOT NULL DEFAULT 0,
                last_updated      TEXT NOT NULL
            );
            """
        )
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(settings.generator_db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
