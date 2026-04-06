"""
Tests for src/swarm/momentum.py — MomentumTracker and CrossSourceAmplifier.
Uses an in-memory SQLite path (tmp_db fixture) to avoid touching generator.db.
"""

from unittest.mock import patch

import pytest

from src.schemas import TAXONOMY_TAGS, RawDocument
from src.swarm.momentum import MomentumTracker
from src.swarm.query_engine import CrossSourceAmplifier
from tests.conftest import make_raw_doc

# ── MomentumTracker ────────────────────────────────────────────────────────────


class TestMomentumTracker:
    def _tracker(self, db_path: str) -> MomentumTracker:
        with patch("src.swarm.momentum.settings") as mock_settings:
            mock_settings.generator_db_path = db_path
            tracker = MomentumTracker.__new__(MomentumTracker)
            tracker._init_db = MomentumTracker._init_db.__get__(tracker, MomentumTracker)
            # Patch settings inside the instance methods
        with patch("src.swarm.momentum.settings") as ms:
            ms.generator_db_path = db_path
            tracker = MomentumTracker()
        return tracker

    def test_record_cycle_writes_all_taxonomy_tags(self, tmp_db: str) -> None:
        with patch("src.swarm.momentum.settings") as ms:
            ms.generator_db_path = tmp_db
            tracker = MomentumTracker()
            tracker.record_cycle({"AI Engineering": 5, "MLOps": 2})

        import sqlite3
        conn = sqlite3.connect(tmp_db)
        rows = conn.execute("SELECT tag, count FROM momentum_cycles").fetchall()
        conn.close()

        tag_map = {r[0]: r[1] for r in rows}
        # All taxonomy tags written
        assert len(tag_map) == len(TAXONOMY_TAGS)
        assert tag_map["AI Engineering"] == 5
        assert tag_map["MLOps"] == 2
        # Tags not in input default to 0
        assert tag_map["Edge Computing"] == 0

    def test_get_baseline_returns_1_when_no_history(self, tmp_db: str) -> None:
        with patch("src.swarm.momentum.settings") as ms:
            ms.generator_db_path = tmp_db
            tracker = MomentumTracker()
            baseline = tracker.get_baseline("AI Engineering")
        assert baseline == 1.0

    def test_get_baseline_averages_last_n_cycles(self, tmp_db: str) -> None:
        with patch("src.swarm.momentum.settings") as ms:
            ms.generator_db_path = tmp_db
            tracker = MomentumTracker()

            # Record 3 cycles with different counts
            tracker.record_cycle({"AI Engineering": 2})
            tracker.record_cycle({"AI Engineering": 4})
            tracker.record_cycle({"AI Engineering": 6})

            baseline = tracker.get_baseline("AI Engineering", lookback_cycles=3)

        # Average of 2, 4, 6 = 4.0
        assert baseline == pytest.approx(4.0)

    def test_compute_snapshots_velocity_calculated(self, tmp_db: str) -> None:
        with patch("src.swarm.momentum.settings") as ms:
            ms.generator_db_path = tmp_db
            tracker = MomentumTracker()

            # Record a baseline of 2 docs per cycle for "AI Engineering"
            tracker.record_cycle({"AI Engineering": 2})
            tracker.record_cycle({"AI Engineering": 2})

            # Current cycle: spike to 8
            snapshots = tracker.compute_snapshots({"AI Engineering": 8})

        ai_snap = next(s for s in snapshots if s.tag == "AI Engineering")
        assert ai_snap.count_this_cycle == 8
        # Velocity = 8 / 2 = 4.0 (way above 1.5 threshold)
        assert ai_snap.velocity > 1.5

    def test_hot_tags_sorted_by_velocity_descending(self, tmp_db: str) -> None:
        with patch("src.swarm.momentum.settings") as ms:
            ms.generator_db_path = tmp_db
            tracker = MomentumTracker()

            # Baseline = 1.0 for all (no history)
            hot = tracker.get_hot_tags({"AI Engineering": 5, "MLOps": 3})

        # Both should be hot (velocity > 1.5, count ≥ 3)
        assert "AI Engineering" in hot
        assert "MLOps" in hot
        # AI Engineering (velocity=5) should come before MLOps (velocity=3)
        assert hot.index("AI Engineering") < hot.index("MLOps")

    def test_unknown_tags_ignored_in_record_cycle(self, tmp_db: str) -> None:
        with patch("src.swarm.momentum.settings") as ms:
            ms.generator_db_path = tmp_db
            tracker = MomentumTracker()
            # "InvalidTag" is not in TAXONOMY_TAGS
            tracker.record_cycle({"InvalidTag": 100, "AI Engineering": 3})

        import sqlite3
        conn = sqlite3.connect(tmp_db)
        rows = conn.execute(
            "SELECT tag FROM momentum_cycles WHERE tag = 'InvalidTag'"
        ).fetchall()
        conn.close()
        assert rows == []


# ── CrossSourceAmplifier ───────────────────────────────────────────────────────


class TestCrossSourceAmplifier:
    def _amplifier(self, db_path: str) -> CrossSourceAmplifier:
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = db_path
            return CrossSourceAmplifier()

    def test_extract_entities_finds_named_entities(self, tmp_db: str) -> None:
        amp = self._amplifier(tmp_db)
        docs = [
            RawDocument.model_validate(make_raw_doc(
                title="Flash Attention Three Optimization",
                source="arxiv",
                source_id="arxiv-001",
            )),
            RawDocument.model_validate(make_raw_doc(
                title="Flash Attention Three Benchmark Results",
                source="github",
                source_id="github-001",
            )),
        ]
        entities = amp.extract_entities(docs)
        # "Flash Attention" or "Attention Three" should appear
        assert any("Flash" in k or "Attention" in k for k in entities)

    def test_get_amplified_signals_requires_min_sources(self, tmp_db: str) -> None:
        amp = self._amplifier(tmp_db)
        docs = [
            RawDocument.model_validate(make_raw_doc(
                title="Flash Attention Three Performance",
                source="arxiv",
                source_id="src-a",
            )),
            RawDocument.model_validate(make_raw_doc(
                title="Flash Attention Three Benchmark",
                source="github",
                source_id="src-b",
            )),
            RawDocument.model_validate(make_raw_doc(
                title="Only Here Once Paper",
                source="arxiv",
                source_id="src-a",
            )),
        ]
        signals = amp.get_amplified_signals(docs, min_sources=2)
        # "Flash Attention Three" appears in 2 different sources → amplified
        assert len(signals) >= 1

    def test_get_amplified_signals_capped_at_10(self, tmp_db: str) -> None:
        amp = self._amplifier(tmp_db)
        # Generate 20 docs all mentioning different entities from 2+ sources
        docs: list[RawDocument] = []
        for i in range(20):
            docs.append(RawDocument.model_validate(make_raw_doc(
                title=f"Alpha Beta Gamma {i} Paper",
                source="arxiv" if i % 2 == 0 else "github",
                source_id=f"src-{i}",
            )))
        signals = amp.get_amplified_signals(docs, min_sources=1)
        assert len(signals) <= 10

    def test_persist_and_load_signals(self, tmp_db: str) -> None:
        amp = self._amplifier(tmp_db)
        signals = ["Flash Attention", "vLLM Serving", "CUDA Kernel"]
        source_counts = {"Flash Attention": 3, "vLLM Serving": 2, "CUDA Kernel": 2}

        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            amp.persist_signals(signals, source_counts)
            loaded = amp.load_recent_signals(hours=24)

        assert "Flash Attention" in loaded
        assert "vLLM Serving" in loaded

    def test_load_recent_signals_empty_when_table_missing(self, tmp_db: str) -> None:
        # A fresh DB with no amplified_signals table — should return []
        import sqlite3
        fresh_db = tmp_db + "_fresh"
        conn = sqlite3.connect(fresh_db)
        conn.close()

        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = fresh_db
            amp = CrossSourceAmplifier.__new__(CrossSourceAmplifier)
            # Skip _init_db so table doesn't exist
            amp._ENTITY_RE = CrossSourceAmplifier._ENTITY_RE
            result = amp.load_recent_signals(hours=6)

        assert result == []
