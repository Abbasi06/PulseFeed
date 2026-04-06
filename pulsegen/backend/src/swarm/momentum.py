"""
Tracks per-taxonomy-tag document frequency across cycles.
Uses SQLite (generator.db) for persistence.
Detects velocity spikes that indicate emerging hot topics.
"""

import logging
import sqlite3
from datetime import UTC, datetime

from src.config import settings
from src.schemas import TAXONOMY_TAGS, MomentumSnapshot

logger = logging.getLogger(__name__)


class MomentumTracker:
    """
    Persists cycle counts in SQLite table `momentum_cycles`:

      CREATE TABLE IF NOT EXISTS momentum_cycles (
        tag      TEXT    NOT NULL,
        cycle_ts TEXT    NOT NULL,   -- ISO datetime of cycle start
        count    INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (tag, cycle_ts)
      )

    A new cycle_ts is minted once per call to ``record_cycle`` so that
    multiple calls within the same second do not silently collide; the
    timestamp is returned so callers can correlate records if needed.
    """

    def __init__(self) -> None:
        self._init_db()

    # ─── Public API ──────────────────────────────────────────────────────────

    def record_cycle(self, tag_counts: dict[str, int]) -> str:
        """
        Insert one row per tag for the current UTC timestamp.

        Only tags present in TAXONOMY_TAGS are persisted; unknown tags are
        silently skipped.  Tags in TAXONOMY_TAGS but absent from *tag_counts*
        are recorded with count=0 so the baseline calculation stays smooth.

        Returns the cycle_ts string that was written.
        """
        cycle_ts = datetime.now(UTC).isoformat()

        rows: list[tuple[str, str, int]] = [
            (tag, cycle_ts, tag_counts.get(tag, 0))
            for tag in TAXONOMY_TAGS
        ]

        with sqlite3.connect(settings.generator_db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executemany(
                "INSERT OR REPLACE INTO momentum_cycles (tag, cycle_ts, count) VALUES (?, ?, ?)",
                rows,
            )
            conn.commit()

        logger.debug("Recorded momentum cycle ts=%s tags=%d", cycle_ts, len(rows))
        return cycle_ts

    def get_baseline(self, tag: str, lookback_cycles: int = 10) -> float:
        """
        Return the rolling average count for *tag* over the last
        *lookback_cycles* cycle timestamps.

        Uses a sub-query to grab the *lookback_cycles* most recent distinct
        cycle timestamps, then averages the count values for *tag* within
        that window.  Returns 1.0 when there is no history so that velocity
        calculations do not divide by zero.
        """
        sql = """
            SELECT AVG(count)
            FROM momentum_cycles
            WHERE tag = ?
              AND cycle_ts IN (
                  SELECT DISTINCT cycle_ts
                  FROM momentum_cycles
                  ORDER BY cycle_ts DESC
                  LIMIT ?
              )
        """
        with sqlite3.connect(settings.generator_db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            row = conn.execute(sql, (tag, lookback_cycles)).fetchone()

        if row is None or row[0] is None:
            return 1.0

        return float(row[0]) if row[0] > 0 else 1.0

    def compute_snapshots(self, tag_counts: dict[str, int]) -> list[MomentumSnapshot]:
        """
        Compute a MomentumSnapshot for every tag in TAXONOMY_TAGS.

        The baseline is derived from *persisted* history (i.e. before this
        cycle's ``record_cycle`` call), so call this *before* calling
        ``record_cycle`` if you want a pure comparison against prior cycles.
        """
        snapshots: list[MomentumSnapshot] = []

        for tag in TAXONOMY_TAGS:
            count_this_cycle = tag_counts.get(tag, 0)
            baseline = self.get_baseline(tag)
            velocity = count_this_cycle / baseline if baseline > 0 else 1.0

            snapshots.append(
                MomentumSnapshot(
                    tag=tag,
                    count_this_cycle=count_this_cycle,
                    baseline_count=baseline,
                    velocity=velocity,
                )
            )

        return snapshots

    def get_hot_tags(self, tag_counts: dict[str, int]) -> list[str]:
        """
        Return names of tags whose MomentumSnapshot.is_hot property is True.

        Tags are returned sorted by velocity descending so callers can
        prioritise the hottest ones when budgets are limited.
        """
        snapshots = self.compute_snapshots(tag_counts)
        hot = [s for s in snapshots if s.is_hot]
        hot.sort(key=lambda s: s.velocity, reverse=True)
        return [s.tag for s in hot]

    # ─── Private helpers ─────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create the momentum_cycles table if it does not exist."""
        with sqlite3.connect(settings.generator_db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS momentum_cycles (
                    tag      TEXT    NOT NULL,
                    cycle_ts TEXT    NOT NULL,
                    count    INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (tag, cycle_ts)
                )
                """
            )
            conn.commit()

        logger.debug("MomentumTracker: DB initialised at %s", settings.generator_db_path)


def _run_trend_job() -> dict[str, object]:
    """
    Module-level function called by trend_analysis_cycle Celery task.
    Reads 30 most-recent summaries from generator_documents, runs
    TrendAnalystAgent from the existing backend generator module (if available),
    and persists results to the trend_keywords table.
    Falls back gracefully if the legacy module is not present.
    """
    import uuid
    from datetime import UTC, datetime

    try:
        conn = sqlite3.connect(settings.generator_db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        rows = conn.execute(
            "SELECT summary FROM generator_documents ORDER BY processed_at DESC LIMIT 30"
        ).fetchall()
        conn.close()
    except Exception as exc:
        logger.warning("_run_trend_job: could not read documents: %s", exc)
        return {"error": str(exc)}

    if not rows:
        logger.info("_run_trend_job: no documents yet, skipping")
        return {"docs_analyzed": 0, "trends_found": 0}

    corpus = "\n\n".join(row[0] for row in rows if row[0])
    run_id = str(uuid.uuid4())
    collected_at = datetime.now(UTC).isoformat()

    try:
        # Use existing TrendAnalystAgent if the legacy backend is on PYTHONPATH
        from generator.trend_analyst import TrendAnalystAgent  # type: ignore[import,unused-ignore]

        agent = TrendAnalystAgent()
        result = agent.analyze(corpus)
        trends = result.extracted_trends
    except ImportError:
        logger.info("_run_trend_job: TrendAnalystAgent not available, skipping")
        return {"docs_analyzed": len(rows), "trends_found": 0, "note": "agent_unavailable"}
    except Exception as exc:
        logger.error("_run_trend_job: TrendAnalystAgent failed: %s", exc)
        return {"error": str(exc)}

    if not trends:
        return {"docs_analyzed": len(rows), "trends_found": 0}

    try:
        conn = sqlite3.connect(settings.generator_db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS trend_keywords (
                run_id TEXT, term TEXT, category TEXT, context TEXT,
                source_count INTEGER, collected_at TEXT
            )"""
        )
        for t in trends:
            conn.execute(
                "INSERT INTO trend_keywords (run_id, term, category, context, source_count, collected_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, t.term, t.category.value, t.context, len(rows), collected_at),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("_run_trend_job: failed to persist trends: %s", exc)

    logger.info(
        "_run_trend_job complete: analyzed=%d found=%d run_id=%s",
        len(rows),
        len(trends),
        run_id,
    )
    return {"docs_analyzed": len(rows), "trends_found": len(trends), "run_id": run_id}
