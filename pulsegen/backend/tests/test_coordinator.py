"""
Tests for SwarmCoordinator budget logic and query planning.
SQLite is redirected to a temp file via tmp_db fixture.
"""

from unittest.mock import patch

from src.schemas import SourceQualityRecord
from src.swarm.coordinator import BASE_FETCH_BUDGET, SwarmCoordinator


def _make_coordinator(db_path: str) -> SwarmCoordinator:
    with patch("src.swarm.coordinator.settings") as ms, \
         patch("src.swarm.momentum.settings") as ms2, \
         patch("src.swarm.query_engine.settings") as ms3:
        ms.generator_db_path = db_path
        ms2.generator_db_path = db_path
        ms3.generator_db_path = db_path
        return SwarmCoordinator()


class TestComputeBudget:
    def _budget(
        self,
        db_path: str,
        record: SourceQualityRecord | None,
        hot_tags: list[str],
    ) -> int:
        coord = _make_coordinator(db_path)
        return coord._compute_budget(record, hot_tags)

    def test_no_history_returns_base_budget(self, tmp_db: str) -> None:
        budget = self._budget(tmp_db, record=None, hot_tags=[])
        assert budget == BASE_FETCH_BUDGET

    def test_perfect_pass_rate_doubles_budget(self, tmp_db: str) -> None:
        record = SourceQualityRecord(
            source_id="arxiv",
            total_fetched=100,
            total_passed_gate=100,
            total_stored=90,
        )
        budget = self._budget(tmp_db, record, hot_tags=[])
        # pass_rate=1.0 → multiplier=0.5+1.5=2.0 → 30*2=60
        assert budget == 60

    def test_zero_pass_rate_halves_budget(self, tmp_db: str) -> None:
        record = SourceQualityRecord(
            source_id="devto",
            total_fetched=100,
            total_passed_gate=0,
            total_stored=0,
        )
        budget = self._budget(tmp_db, record, hot_tags=[])
        # pass_rate=0 → multiplier=0.5 → 30*0.5=15
        assert budget == 15

    def test_hot_tags_add_20_percent_bonus(self, tmp_db: str) -> None:
        budget_cold = self._budget(tmp_db, record=None, hot_tags=[])
        budget_hot = self._budget(tmp_db, record=None, hot_tags=["AI Engineering"])
        assert budget_hot == int(budget_cold * 1.2)

    def test_budget_minimum_is_10(self, tmp_db: str) -> None:
        # Even with very low pass rate, budget >= 10
        record = SourceQualityRecord(
            source_id="rss",
            total_fetched=10000,
            total_passed_gate=0,
            total_stored=0,
        )
        budget = self._budget(tmp_db, record, hot_tags=[])
        assert budget >= 10

    def test_budget_maximum_is_100(self, tmp_db: str) -> None:
        # Perfect pass rate + hot tags should not exceed 100
        record = SourceQualityRecord(
            source_id="arxiv",
            total_fetched=100,
            total_passed_gate=100,
            total_stored=100,
        )
        budget = self._budget(tmp_db, record, hot_tags=["AI Engineering", "MLOps"])
        assert budget <= 100

    def test_plan_cycle_returns_all_sources(self, tmp_db: str) -> None:
        coord = _make_coordinator(tmp_db)
        with patch.object(coord._momentum, "record_cycle"), \
             patch.object(coord._momentum, "compute_snapshots", return_value=[]), \
             patch.object(coord._amplifier, "load_recent_signals", return_value=[]):
            plan = coord.plan_cycle({})

        from src.swarm.coordinator import ALL_SOURCE_IDS
        for source_id in ALL_SOURCE_IDS:
            assert source_id in plan

    def test_plan_cycle_budget_and_query_set_per_source(self, tmp_db: str) -> None:
        coord = _make_coordinator(tmp_db)
        with patch.object(coord._momentum, "record_cycle"), \
             patch.object(coord._momentum, "compute_snapshots", return_value=[]), \
             patch.object(coord._amplifier, "load_recent_signals", return_value=[]):
            plan = coord.plan_cycle({})

        for source_id, (budget, query_set) in plan.items():
            assert isinstance(budget, int)
            assert budget >= 10
            assert len(query_set.queries) > 0

    def test_record_harvest_result_creates_new_record(self, tmp_db: str) -> None:
        coord = _make_coordinator(tmp_db)
        with patch("src.swarm.coordinator.settings") as ms, \
             patch("src.swarm.query_engine.settings") as ms2:
            ms.generator_db_path = tmp_db
            ms2.generator_db_path = tmp_db
            coord.record_harvest_result(
                source_id="arxiv",
                fetched=50,
                passed_gate=30,
                stored=25,
            )
            records = coord._load_quality_records()
        assert "arxiv" in records
        assert records["arxiv"].total_fetched == 50

    def test_record_harvest_result_accumulates(self, tmp_db: str) -> None:
        coord = _make_coordinator(tmp_db)
        with patch("src.swarm.coordinator.settings") as ms, \
             patch("src.swarm.query_engine.settings") as ms2:
            ms.generator_db_path = tmp_db
            ms2.generator_db_path = tmp_db
            coord.record_harvest_result("github", fetched=20, passed_gate=10, stored=8)
            coord.record_harvest_result("github", fetched=30, passed_gate=20, stored=18)
            records = coord._load_quality_records()
        assert records["github"].total_fetched == 50
        assert records["github"].total_passed_gate == 30
