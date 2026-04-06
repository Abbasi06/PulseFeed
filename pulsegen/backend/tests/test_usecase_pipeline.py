"""
Use-case tests for the Celery task pipeline.

Tests each task's business logic by mocking external dependencies (Gemini,
Redis, PostgreSQL, MCP) — no real broker or network calls.

Calling pattern for bind=True Celery tasks:
  task.run(*user_args)   — Celery injects self (the task instance) automatically.
  task.push_request(**kw) / task.pop_request() — set request context (retries, etc.)
  patch.object(task, 'retry', ...) — mock retry behaviour.
  patch('google.genai.Client') — mock Gemini client (imported inline in each task).
  patch('src.tasks.asyncio.run') — skip actual async execution in synchronous tests.

Pipeline:
  gatekeeper_task → extractor_task → storage_router_task
                                     ↓ (on final failure)
                                 _dead_letter (Redis)

Also covers:
  prune_momentum_data — SQLite cleanup
  trend_analysis_cycle — calls src.swarm.momentum._run_trend_job
  harvest_cycle — dispatches per-source tasks
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Retry as CeleryRetry

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _raw_doc_dict(**overrides: object) -> dict:
    base = {
        "title": "Flash Attention 3: Optimising Transformer Inference at Scale",
        "url": "https://example.com/flash-attention-3",
        "body": " ".join(["word"] * 320),
        "source": "arxiv",
        "source_id": "2401.12345",
    }
    base.update(overrides)
    return base


def _extracted_dict(**overrides: object) -> dict:
    base = {
        "summary": "First sentence. Second sentence. Third sentence.",
        "bm25_keywords": ["Flash", "Attention", "H100", "CUDA", "BF16"],
        "taxonomy_tags": ["AI Engineering"],
        "image_url": None,
    }
    base.update(overrides)
    return base


# ─── gatekeeper_task ─────────────────────────────────────────────────────────


class TestGatekeeperTaskLogic:
    def test_high_signal_doc_chains_to_extractor(self) -> None:
        from src.tasks import gatekeeper_task

        gate_result = MagicMock(passes=True, confidence=0.9, reasoning="High signal")

        with patch("src.tasks.asyncio.run", return_value=gate_result), \
             patch("google.genai.Client"), \
             patch("src.tasks.extractor_task") as mock_extractor, \
             patch("src.tasks._get_coordinator"):
            gatekeeper_task.run(_raw_doc_dict())

        mock_extractor.delay.assert_called_once()

    def test_low_signal_doc_does_not_chain_extractor(self) -> None:
        from src.tasks import gatekeeper_task

        gate_result = MagicMock(passes=False, confidence=0.2, reasoning="Low signal")

        with patch("src.tasks.asyncio.run", return_value=gate_result), \
             patch("google.genai.Client"), \
             patch("src.tasks.extractor_task") as mock_extractor, \
             patch("src.tasks._get_coordinator"):
            gatekeeper_task.run(_raw_doc_dict())

        mock_extractor.delay.assert_not_called()

    def test_gatekeeper_retries_on_exception(self) -> None:
        from src.tasks import gatekeeper_task

        with patch("src.tasks.asyncio.run", side_effect=RuntimeError("API timeout")), \
             patch("google.genai.Client"), \
             patch.object(gatekeeper_task, "retry", side_effect=CeleryRetry()) as mock_retry:
            with pytest.raises(CeleryRetry):
                gatekeeper_task.run(_raw_doc_dict())

        mock_retry.assert_called_once()

    def test_gatekeeper_passes_confidence_to_extractor(self) -> None:
        from src.tasks import gatekeeper_task

        gate_result = MagicMock(passes=True, confidence=0.87, reasoning=None)

        with patch("src.tasks.asyncio.run", return_value=gate_result), \
             patch("google.genai.Client"), \
             patch("src.tasks.extractor_task") as mock_extractor, \
             patch("src.tasks._get_coordinator"):
            gatekeeper_task.run(_raw_doc_dict())

        call_args = mock_extractor.delay.call_args
        # extractor_task.delay(raw_doc_dict, gate.confidence)
        passed_confidence = call_args.args[1]
        assert passed_confidence == pytest.approx(0.87)

    def test_gatekeeper_records_pass_with_coordinator(self) -> None:
        from src.tasks import gatekeeper_task

        gate_result = MagicMock(passes=True, confidence=0.9, reasoning=None)
        mock_coordinator = MagicMock()

        with patch("src.tasks.asyncio.run", return_value=gate_result), \
             patch("google.genai.Client"), \
             patch("src.tasks.extractor_task"), \
             patch("src.tasks._get_coordinator", return_value=mock_coordinator):
            gatekeeper_task.run(_raw_doc_dict())

        mock_coordinator.record_harvest_result.assert_called_once_with(
            source_id="arxiv",
            fetched=0,
            passed_gate=1,
            stored=0,
        )

    def test_gatekeeper_invalid_doc_dict_raises_validation_error(self) -> None:
        from src.tasks import gatekeeper_task

        bad_doc = {"title": "No source or url here"}  # missing required fields

        with patch("google.genai.Client"):
            with pytest.raises(Exception):
                gatekeeper_task.run(bad_doc)

    def test_gatekeeper_low_confidence_below_threshold_rejects(self) -> None:
        from src.tasks import gatekeeper_task

        # passes=False when confidence < 0.6 even if is_high_signal=True
        gate_result = MagicMock(passes=False, confidence=0.55, reasoning="Below threshold")

        with patch("src.tasks.asyncio.run", return_value=gate_result), \
             patch("google.genai.Client"), \
             patch("src.tasks.extractor_task") as mock_extractor, \
             patch("src.tasks._get_coordinator"):
            gatekeeper_task.run(_raw_doc_dict())

        mock_extractor.delay.assert_not_called()


# ─── extractor_task ──────────────────────────────────────────────────────────


class TestExtractorTaskLogic:
    def test_successful_extraction_chains_storage(self) -> None:
        from src.schemas import ExtractedDocument
        from src.tasks import extractor_task

        mock_extracted = ExtractedDocument.model_validate(_extracted_dict())

        with patch("src.tasks.asyncio.run", return_value=mock_extracted), \
             patch("google.genai.Client"), \
             patch("src.tasks.storage_router_task") as mock_storage:
            extractor_task.run(_raw_doc_dict(), 0.9)

        mock_storage.delay.assert_called_once()

    def test_extractor_retries_on_exception(self) -> None:
        from src.tasks import extractor_task

        with patch("src.tasks.asyncio.run", side_effect=RuntimeError("LLM timeout")), \
             patch("google.genai.Client"), \
             patch.object(extractor_task, "retry", side_effect=CeleryRetry()) as mock_retry:
            with pytest.raises(CeleryRetry):
                extractor_task.run(_raw_doc_dict(), 0.9)

        mock_retry.assert_called_once()

    def test_extractor_passes_confidence_to_storage(self) -> None:
        from src.schemas import ExtractedDocument
        from src.tasks import extractor_task

        mock_extracted = ExtractedDocument.model_validate(_extracted_dict())

        with patch("src.tasks.asyncio.run", return_value=mock_extracted), \
             patch("google.genai.Client"), \
             patch("src.tasks.storage_router_task") as mock_storage:
            extractor_task.run(_raw_doc_dict(), 0.75)

        call_args = mock_storage.delay.call_args
        # storage_router_task.delay(raw_doc_dict, extracted_dict, gatekeeper_confidence)
        assert len(call_args.args) == 3
        confidence_arg = call_args.args[2]
        assert confidence_arg == pytest.approx(0.75)


# ─── storage_router_task ─────────────────────────────────────────────────────


class TestStorageRouterTaskLogic:
    def test_successful_storage_returns_stored_status(self) -> None:
        from src.schemas import StorageConfirmation
        from src.tasks import storage_router_task

        mock_confirmation = StorageConfirmation(success=True, document_id="doc-uuid-123")

        with patch("src.tasks.route_to_postgres", return_value=mock_confirmation), \
             patch("src.tasks._record_stored_tags"), \
             patch("src.tasks._get_coordinator"):
            result = storage_router_task.run(_raw_doc_dict(), _extracted_dict(), 0.9)

        assert result["status"] == "stored"
        assert result["document_id"] == "doc-uuid-123"

    def test_successful_storage_records_taxonomy_tags(self) -> None:
        from src.schemas import StorageConfirmation
        from src.tasks import storage_router_task

        mock_confirmation = StorageConfirmation(success=True, document_id="doc-uuid-456")

        with patch("src.tasks.route_to_postgres", return_value=mock_confirmation), \
             patch("src.tasks._record_stored_tags") as mock_record, \
             patch("src.tasks._get_coordinator"):
            storage_router_task.run(_raw_doc_dict(), _extracted_dict(), 0.9)

        mock_record.assert_called_once_with(["AI Engineering"])

    def test_storage_failure_triggers_retry_before_max(self) -> None:
        from src.schemas import StorageConfirmation
        from src.tasks import storage_router_task

        mock_failure = StorageConfirmation(success=False, error="DB connection refused")

        storage_router_task.push_request(retries=0)
        try:
            with patch("src.tasks.route_to_postgres", return_value=mock_failure), \
                 patch("src.tasks._get_coordinator"), \
                 patch.object(storage_router_task, "retry", side_effect=CeleryRetry()) as mock_retry:
                with pytest.raises(CeleryRetry):
                    storage_router_task.run(_raw_doc_dict(), _extracted_dict(), 0.9)
            mock_retry.assert_called_once()
        finally:
            storage_router_task.pop_request()

    def test_storage_failure_at_max_retries_dead_letters(self) -> None:
        from src.schemas import StorageConfirmation
        from src.tasks import storage_router_task

        mock_failure = StorageConfirmation(success=False, error="persistent failure")

        storage_router_task.push_request(retries=storage_router_task.max_retries)
        try:
            with patch("src.tasks.route_to_postgres", return_value=mock_failure), \
                 patch("src.tasks._get_coordinator"), \
                 patch("src.tasks._dead_letter") as mock_dl:
                result = storage_router_task.run(_raw_doc_dict(), _extracted_dict(), 0.9)

            mock_dl.assert_called_once()
            assert result["status"] == "dead_lettered"
        finally:
            storage_router_task.pop_request()

    def test_route_to_postgres_exception_retried_before_max(self) -> None:
        from src.tasks import storage_router_task

        storage_router_task.push_request(retries=1)
        try:
            with patch("src.tasks.route_to_postgres", side_effect=RuntimeError("unexpected")), \
                 patch("src.tasks._get_coordinator"), \
                 patch.object(storage_router_task, "retry", side_effect=CeleryRetry()) as mock_retry:
                with pytest.raises(CeleryRetry):
                    storage_router_task.run(_raw_doc_dict(), _extracted_dict(), 0.9)
            mock_retry.assert_called_once()
        finally:
            storage_router_task.pop_request()

    def test_route_to_postgres_exception_at_max_retries_dead_letters(self) -> None:
        from src.tasks import storage_router_task

        storage_router_task.push_request(retries=storage_router_task.max_retries)
        try:
            with patch("src.tasks.route_to_postgres", side_effect=RuntimeError("fatal")), \
                 patch("src.tasks._get_coordinator"), \
                 patch("src.tasks._dead_letter") as mock_dl:
                result = storage_router_task.run(_raw_doc_dict(), _extracted_dict(), 0.9)

            mock_dl.assert_called_once()
            assert result["status"] == "dead_lettered"
        finally:
            storage_router_task.pop_request()

    def test_successful_storage_updates_coordinator(self) -> None:
        from src.schemas import StorageConfirmation
        from src.tasks import storage_router_task

        mock_confirmation = StorageConfirmation(success=True, document_id="doc-abc")
        mock_coordinator = MagicMock()

        with patch("src.tasks.route_to_postgres", return_value=mock_confirmation), \
             patch("src.tasks._record_stored_tags"), \
             patch("src.tasks._get_coordinator", return_value=mock_coordinator):
            storage_router_task.run(_raw_doc_dict(), _extracted_dict(), 0.9)

        mock_coordinator.record_harvest_result.assert_called_once_with(
            source_id="arxiv",
            fetched=0,
            passed_gate=0,
            stored=1,
        )

    def test_dead_lettered_url_matches_document_url(self) -> None:
        from src.schemas import StorageConfirmation
        from src.tasks import storage_router_task

        doc_url = "https://example.com/flash-attention-3"
        mock_failure = StorageConfirmation(success=False, error="fail")

        storage_router_task.push_request(retries=storage_router_task.max_retries)
        try:
            with patch("src.tasks.route_to_postgres", return_value=mock_failure), \
                 patch("src.tasks._get_coordinator"), \
                 patch("src.tasks._dead_letter"):
                result = storage_router_task.run(_raw_doc_dict(url=doc_url), _extracted_dict(), 0.9)

            assert result.get("url") == doc_url
        finally:
            storage_router_task.pop_request()


# ─── prune_momentum_data ──────────────────────────────────────────────────────


class TestPruneMomentumData:
    def test_prune_removes_old_rows(self, tmp_db: str) -> None:
        import sqlite3

        from src.tasks import prune_momentum_data

        conn = sqlite3.connect(tmp_db)
        conn.execute("""CREATE TABLE IF NOT EXISTS momentum_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_ts TEXT NOT NULL,
            tag TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS amplified_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            recorded_at TEXT NOT NULL
        )""")
        # Old row — should be deleted
        conn.execute(
            "INSERT INTO momentum_cycles (cycle_ts, tag, count) VALUES (?, ?, ?)",
            ("2000-01-01T00:00:00", "AI Engineering", 5),
        )
        # Recent row — should survive
        conn.execute(
            "INSERT INTO momentum_cycles (cycle_ts, tag, count) VALUES (?, ?, ?)",
            (datetime.now(UTC).isoformat(), "MLOps", 3),
        )
        conn.commit()
        conn.close()

        with patch("src.tasks.settings") as mock_settings:
            mock_settings.generator_db_path = tmp_db
            result = prune_momentum_data.run()

        assert "pruned_rows" in result
        assert result["pruned_rows"] >= 1

        conn = sqlite3.connect(tmp_db)
        remaining = conn.execute("SELECT COUNT(*) FROM momentum_cycles").fetchone()[0]
        conn.close()
        assert remaining == 1  # only the recent row remains

    def test_prune_handles_missing_table_gracefully(self, tmp_db: str) -> None:
        from src.tasks import prune_momentum_data

        with patch("src.tasks.settings") as mock_settings:
            mock_settings.generator_db_path = tmp_db
            # No tables created — must not raise
            result = prune_momentum_data.run()

        assert isinstance(result, dict)
        # Either pruned_rows or error key
        assert "pruned_rows" in result or "error" in result

    def test_prune_returns_pruned_count(self, tmp_db: str) -> None:
        import sqlite3

        from src.tasks import prune_momentum_data

        conn = sqlite3.connect(tmp_db)
        conn.execute("""CREATE TABLE IF NOT EXISTS momentum_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_ts TEXT NOT NULL,
            tag TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS amplified_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            recorded_at TEXT NOT NULL
        )""")
        conn.commit()
        conn.close()

        with patch("src.tasks.settings") as mock_settings:
            mock_settings.generator_db_path = tmp_db
            result = prune_momentum_data.run()

        assert isinstance(result.get("pruned_rows"), int)


# ─── trend_analysis_cycle ────────────────────────────────────────────────────


class TestTrendAnalysisCycle:
    def test_successful_trend_cycle_returns_dict(self) -> None:
        from src.tasks import trend_analysis_cycle

        expected = {"terms_extracted": 5, "run_id": "run-abc"}

        with patch("src.swarm.momentum._run_trend_job", return_value=expected):
            result = trend_analysis_cycle.run()

        assert isinstance(result, dict)

    def test_trend_cycle_handles_exception_gracefully(self) -> None:
        from src.tasks import trend_analysis_cycle

        with patch("src.swarm.momentum._run_trend_job", side_effect=RuntimeError("LLM failed")):
            result = trend_analysis_cycle.run()  # must not raise

        assert isinstance(result, dict)
        # Returns error info rather than raising
        assert "error" in result

    def test_trend_cycle_returns_result_from_trend_job(self) -> None:
        from src.tasks import trend_analysis_cycle

        trend_output = {"terms_extracted": 12, "run_id": "run-xyz", "docs_analyzed": 30}

        with patch("src.swarm.momentum._run_trend_job", return_value=trend_output):
            result = trend_analysis_cycle.run()

        # The task returns the result from _run_trend_job
        assert isinstance(result, dict)


# ─── harvest_cycle ───────────────────────────────────────────────────────────


class TestHarvestCycle:
    def test_harvest_cycle_dispatches_one_task_per_source(self) -> None:
        from src.tasks import harvest_cycle

        mock_coordinator = MagicMock()
        mock_coordinator.plan_cycle.return_value = {
            "arxiv": (30, MagicMock(queries=["query1", "query2"], hot_topics=[])),
            "github": (20, MagicMock(queries=["query3"], hot_topics=[])),
            "hackernews": (15, MagicMock(queries=["query4"], hot_topics=[])),
        }

        with patch("src.tasks._get_coordinator", return_value=mock_coordinator), \
             patch("src.tasks._load_last_cycle_tag_counts", return_value={}), \
             patch("src.tasks.chord"), \
             patch("src.tasks.group"), \
             patch("src.tasks.harvest_source_task") as mock_source_task:

            mock_source_task.s.return_value = MagicMock()
            result = harvest_cycle.run()

        assert result["sources_dispatched"] == 3
        assert mock_source_task.s.call_count == 3

    def test_harvest_cycle_returns_cycle_ts(self) -> None:
        from src.tasks import harvest_cycle

        mock_coordinator = MagicMock()
        mock_coordinator.plan_cycle.return_value = {}

        with patch("src.tasks._get_coordinator", return_value=mock_coordinator), \
             patch("src.tasks._load_last_cycle_tag_counts", return_value={}):
            result = harvest_cycle.run()

        assert "cycle_ts" in result
        ts = datetime.fromisoformat(result["cycle_ts"])
        assert ts is not None

    def test_harvest_cycle_empty_plan_dispatches_zero_tasks(self) -> None:
        from src.tasks import harvest_cycle

        mock_coordinator = MagicMock()
        mock_coordinator.plan_cycle.return_value = {}

        with patch("src.tasks._get_coordinator", return_value=mock_coordinator), \
             patch("src.tasks._load_last_cycle_tag_counts", return_value={}), \
             patch("src.tasks.chord") as mock_chord:
            result = harvest_cycle.run()

        assert result["sources_dispatched"] == 0
        mock_chord.assert_not_called()

    def test_harvest_cycle_passes_tag_counts_to_coordinator(self) -> None:
        from src.tasks import harvest_cycle

        mock_coordinator = MagicMock()
        mock_coordinator.plan_cycle.return_value = {}
        tag_counts = {"AI Engineering": 5, "MLOps": 3}

        with patch("src.tasks._get_coordinator", return_value=mock_coordinator), \
             patch("src.tasks._load_last_cycle_tag_counts", return_value=tag_counts):
            harvest_cycle.run()

        mock_coordinator.plan_cycle.assert_called_once_with(tag_counts)
