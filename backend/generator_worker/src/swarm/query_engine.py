"""
Generates source-specific adaptive search queries by blending:
  1. Static taxonomy anchors (precise, battle-tested queries per tag)
  2. Trending keywords from SQLite momentum_cycles + trend_keywords tables
  3. Cross-source amplified hot signals from the current cycle

This ensures we always find content for our taxonomy tags,
but also chase emerging terms that may not yet be in our anchors.
"""

import logging
import random
import re
import sqlite3
from datetime import datetime

from src.config import settings
from src.schemas import TAXONOMY_TAGS, AdaptiveQuerySet, RawDocument

logger = logging.getLogger(__name__)

# ─── Taxonomy anchor queries ──────────────────────────────────────────────────
# These run every cycle regardless of trends — they are the stable spine of
# each source's query budget.

TAXONOMY_ANCHORS: dict[str, list[str]] = {
    "AI Engineering": [
        "LLM inference optimization serving latency",
        "transformer model deployment production",
        "quantization pruning model compression inference",
        "speculative decoding continuous batching vLLM SGLang",
        "LLM serving infrastructure throughput tokens per second",
    ],
    "Agentic Workflows": [
        "AI agent tool use planning reasoning",
        "autonomous agent LLM function calling",
        "multi-agent orchestration coordination",
        "ReAct agent chain-of-thought tool use",
        "agentic system memory retrieval planning",
        "LLM agent benchmark evaluation",
    ],
    "LLMOps": [
        "LLM monitoring observability production deployment",
        "model drift detection prompt monitoring",
        "LLM evaluation framework automated testing",
        "fine-tuning pipeline LoRA QLoRA production",
        "LLM cost optimization token usage tracking",
    ],
    "Distributed Systems": [
        "distributed consensus fault tolerance Raft Paxos",
        "microservices service mesh Kubernetes orchestration",
        "distributed tracing observability OpenTelemetry",
        "event-driven architecture Kafka stream processing",
        "distributed training gradient synchronization NCCL",
    ],
    "Data Engineering": [
        "data pipeline orchestration Airflow dbt Dagster",
        "vector database pgvector Chroma Pinecone Weaviate",
        "real-time streaming Flink Spark structured streaming",
        "data lakehouse Delta Lake Iceberg architecture",
        "feature store MLOps data versioning",
    ],
    "Cybersecurity/Zero-Trust": [
        "zero-trust architecture identity verification",
        "container security Kubernetes RBAC network policy",
        "supply chain security SBOM vulnerability",
        "LLM security prompt injection jailbreak defense",
        "eBPF kernel security runtime protection",
    ],
    "GPU Optimization": [
        "GPU kernel optimization CUDA performance",
        "tensor parallelism pipeline parallelism training",
        "Flash Attention memory efficient transformer",
        "GPU memory bandwidth utilization optimization",
        "mixed precision training BF16 FP8",
        "NVIDIA Hopper H100 GPU architecture",
    ],
    "Edge Computing": [
        "edge inference deployment embedded ML",
        "model compression mobile deployment tflite ONNX",
        "edge AI IoT hardware accelerator NPU",
        "federated learning privacy edge devices",
        "WebAssembly WASM edge serverless deployment",
    ],
    "MLOps": [
        "MLOps model registry versioning deployment",
        "ML pipeline CI/CD automated retraining",
        "model monitoring data drift concept drift",
        "Kubeflow MLflow Weights Biases experiment tracking",
        "A/B testing model serving shadow deployment",
    ],
}

# ArXiv sources benefit from more academic phrasing
ARXIV_EXTRA_QUERIES: dict[str, list[str]] = {
    "AI Engineering": [
        "large language model inference acceleration",
        "transformer serving optimization throughput",
    ],
    "GPU Optimization": [
        "GPU memory bandwidth roofline model neural network",
        "mixed precision training convergence",
    ],
    "Distributed Systems": [
        "Byzantine fault tolerance distributed consensus protocol",
        "geo-distributed latency optimization",
    ],
    "Agentic Workflows": [
        "language model agent tool augmented reasoning planning",
        "multi-agent cooperation emergent behavior",
    ],
    "MLOps": [
        "automated machine learning hyperparameter optimization",
        "continual learning catastrophic forgetting production",
    ],
    "LLMOps": [
        "large language model deployment evaluation benchmark",
        "instruction tuning RLHF alignment fine-tuning",
    ],
    "Data Engineering": [
        "approximate nearest neighbor search high dimensional",
        "streaming graph processing temporal data",
    ],
    "Cybersecurity/Zero-Trust": [
        "adversarial examples robustness machine learning",
        "differential privacy federated learning",
    ],
    "Edge Computing": [
        "neural architecture search resource constrained devices",
        "model pruning knowledge distillation edge",
    ],
}


# ─── DynamicQueryEngine ───────────────────────────────────────────────────────


class DynamicQueryEngine:
    """
    Produces an AdaptiveQuerySet per (source_id, cycle).

    Algorithm per ``build_queries`` call:
    1. Load trending terms from SQLite ``trend_keywords`` table (last 2 run_ids).
    2. Receive hot_tags list (computed by MomentumTracker / SwarmCoordinator).
    3. For each hot tag: pick 2 extra anchor queries + blend with up to 3
       trending terms → produces richer, trend-blended variants.
    4. For non-hot tags: pick 1–2 anchor queries (stable coverage).
    5. For the ``arxiv`` source: append ARXIV_EXTRA_QUERIES for hot tags.
    6. Shuffle, deduplicate, cap at *max_queries*.
    """

    def build_queries(
        self,
        source_id: str,
        hot_tags: list[str],
        amplified_signals: list[str] | None = None,
        max_queries: int = 12,
    ) -> AdaptiveQuerySet:
        """
        Build an AdaptiveQuerySet for *source_id* given the current *hot_tags*.

        Parameters
        ----------
        source_id:
            Connector identifier (e.g. ``"arxiv"``, ``"github"``).
        hot_tags:
            Tags flagged as hot by MomentumTracker this cycle.
        amplified_signals:
            Cross-source entity signals from CrossSourceAmplifier.  When
            provided they are injected as additional query strings after the
            anchor + trend queries, before the final cap is applied.
        max_queries:
            Hard cap on the number of queries returned.

        Returns
        -------
        AdaptiveQuerySet with ``base_queries_count`` and ``trend_queries_count``
        tracking how many queries came from each source.
        """
        trending = self._load_trending_terms(limit=20)
        amplified_signals = amplified_signals or []
        cold_tags = [t for t in TAXONOMY_TAGS if t not in hot_tags]

        base_queries: list[str] = []
        trend_queries: list[str] = []

        # Hot tags — deeper coverage + trend blending
        for tag in hot_tags:
            anchors = TAXONOMY_ANCHORS.get(tag, [])
            if not anchors:
                continue
            # Pick up to 2 anchors for this hot tag
            selected_anchors = random.sample(anchors, min(2, len(anchors)))
            base_queries.extend(selected_anchors)

            # Blend each selected anchor with up to 3 trending terms
            for anchor in selected_anchors:
                blended = self._blend_with_trends(anchor, trending, max_blend=3)
                # First element is the bare anchor (already added above); add only blended variants
                trend_queries.extend(blended[1:])

            # ArXiv extra queries for hot tags
            if source_id == "arxiv":
                extras = ARXIV_EXTRA_QUERIES.get(tag, [])
                base_queries.extend(extras)

        # Non-hot (cold) tags — light coverage to maintain baseline
        for tag in cold_tags:
            anchors = TAXONOMY_ANCHORS.get(tag, [])
            if not anchors:
                continue
            selected = random.sample(anchors, min(2, len(anchors)))
            base_queries.extend(selected)

        # Deduplicate while preserving insertion order
        seen: set[str] = set()
        deduped_base: list[str] = []
        for q in base_queries:
            key = q.lower().strip()
            if key not in seen:
                seen.add(key)
                deduped_base.append(q)

        deduped_trend: list[str] = []
        for q in trend_queries:
            key = q.lower().strip()
            if key not in seen:
                seen.add(key)
                deduped_trend.append(q)

        # Shuffle each bucket to vary order across cycles
        random.shuffle(deduped_base)
        random.shuffle(deduped_trend)

        # Inject cross-source amplified signals (deduped against existing queries)
        deduped_amplified: list[str] = []
        for signal in amplified_signals:
            key = signal.lower().strip()
            if key not in seen:
                seen.add(key)
                deduped_amplified.append(signal)

        # Combine: base → trend enrichments → amplified signals; cap to max_queries
        # Amplified signals are capped to 15 total (generous ceiling) before the
        # max_queries cut so that highly trending entities don't crowd out anchors.
        combined = (deduped_base + deduped_trend + deduped_amplified)[:max(max_queries, 15)]
        combined = combined[:max_queries]

        base_count = min(len(deduped_base), max_queries)
        trend_count = max(0, len(combined) - base_count - len(deduped_amplified))
        trend_count = max(0, trend_count)

        amplified_in_result = min(len(deduped_amplified), max(0, max_queries - base_count - trend_count))
        logger.debug(
            "QueryEngine source=%s hot=%d base=%d trend=%d amplified=%d total=%d",
            source_id,
            len(hot_tags),
            base_count,
            trend_count,
            amplified_in_result,
            len(combined),
        )

        return AdaptiveQuerySet(
            source_id=source_id,
            queries=combined,
            hot_topics=list(hot_tags),
            base_queries_count=base_count,
            trend_queries_count=trend_count + amplified_in_result,
        )

    def _load_trending_terms(self, limit: int = 20) -> list[str]:
        """
        Read distinct trending terms from the ``trend_keywords`` table,
        filtering to the 2 most recent ``run_id`` values.

        Returns an empty list if the table does not exist or the database
        file cannot be opened.
        """
        try:
            with sqlite3.connect(settings.generator_db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")

                # Fetch the 2 most recent run_ids
                run_id_rows = conn.execute(
                    """
                    SELECT DISTINCT run_id
                    FROM trend_keywords
                    ORDER BY collected_at DESC
                    LIMIT 2
                    """
                ).fetchall()

                if not run_id_rows:
                    return []

                run_ids = [r[0] for r in run_id_rows]
                placeholders = ",".join("?" * len(run_ids))

                term_rows = conn.execute(
                    f"""
                    SELECT DISTINCT term
                    FROM trend_keywords
                    WHERE run_id IN ({placeholders})
                    ORDER BY collected_at DESC
                    LIMIT ?
                    """,
                    (*run_ids, limit),
                ).fetchall()

                return [r[0] for r in term_rows if r[0]]

        except sqlite3.OperationalError as exc:
            # Table or DB missing — non-fatal; we fall back to anchors only
            logger.debug("trend_keywords table not available: %s", exc)
            return []

    def _blend_with_trends(
        self,
        anchor: str,
        trending: list[str],
        max_blend: int = 2,
    ) -> list[str]:
        """
        Return *anchor* followed by blended variants formed by appending
        sampled trending terms.

        Example:
            anchor   = "LLM inference optimization serving latency"
            trending = ["Mamba SSM", "Flash Attention 3"]
            result   = [
                "LLM inference optimization serving latency",
                "LLM inference optimization serving latency Mamba SSM",
                "LLM inference optimization serving latency Flash Attention 3",
            ]
        """
        if not trending:
            return [anchor]

        sampled = random.sample(trending, min(max_blend, len(trending)))
        blended = [f"{anchor} {term}" for term in sampled]
        return [anchor] + blended


# ─── CrossSourceAmplifier ─────────────────────────────────────────────────────


class CrossSourceAmplifier:
    """
    After each harvest cycle, detects named entities that were mentioned
    across 2+ different sources.  These become priority signals that get
    prepended to the next cycle's trending terms.

    Persists signals in SQLite table ``amplified_signals``:
        term TEXT PRIMARY KEY, source_count INTEGER, recorded_at TEXT
    """

    # Regex: two or three consecutive Title-Case words (named entity heuristic)
    _ENTITY_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9]+){1,2})\b")

    def __init__(self) -> None:
        self._init_db()

    # ─── Public API ──────────────────────────────────────────────────────────

    def extract_entities(self, docs: list[RawDocument]) -> dict[str, list[str]]:
        """
        Simple keyword extraction: scan titles for capitalized multi-word
        phrases (2–3 words) and record which source_ids mentioned each.

        Returns ``{entity_string: [source_ids]}``.
        """
        entity_sources: dict[str, list[str]] = {}

        for doc in docs:
            matches = self._ENTITY_RE.findall(doc.title)
            source_label = doc.source_id or doc.source.value

            for entity in matches:
                entity_sources.setdefault(entity, [])
                if source_label not in entity_sources[entity]:
                    entity_sources[entity].append(source_label)

        return entity_sources

    def get_amplified_signals(
        self,
        docs: list[RawDocument],
        min_sources: int = 2,
    ) -> list[str]:
        """
        Return entity strings appearing in *min_sources* or more distinct
        sources within *docs*, sorted by mention-source-count descending.

        Capped at 10 signals.
        """
        entity_sources = self.extract_entities(docs)

        qualifying = [
            (entity, sources)
            for entity, sources in entity_sources.items()
            if len(sources) >= min_sources
        ]

        # Sort by number of sources descending, then alphabetically for stability
        qualifying.sort(key=lambda x: (-len(x[1]), x[0]))

        signals = [entity for entity, _ in qualifying[:10]]

        logger.info(
            "CrossSourceAmplifier: %d amplified signals from %d docs",
            len(signals),
            len(docs),
        )
        return signals

    def persist_signals(
        self,
        signals: list[str],
        source_counts: dict[str, int],
    ) -> None:
        """
        Upsert *signals* into the ``amplified_signals`` table.

        *source_counts* maps entity → number of sources that mentioned it.
        Signals absent from *source_counts* default to a count of 1.
        """
        if not signals:
            return

        now = datetime.utcnow().isoformat()
        rows = [
            (term, source_counts.get(term, 1), now)
            for term in signals
        ]

        with sqlite3.connect(settings.generator_db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executemany(
                """
                INSERT INTO amplified_signals (term, source_count, recorded_at)
                VALUES (?, ?, ?)
                ON CONFLICT(term) DO UPDATE SET
                    source_count = excluded.source_count,
                    recorded_at  = excluded.recorded_at
                """,
                rows,
            )
            conn.commit()

        logger.debug("Persisted %d amplified signals", len(rows))

    def load_recent_signals(self, hours: int = 6) -> list[str]:
        """
        Return terms from ``amplified_signals`` recorded within the last
        *hours* hours, ordered by source_count descending.

        Returns an empty list if the table is missing.
        """
        try:
            with sqlite3.connect(settings.generator_db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                rows = conn.execute(
                    """
                    SELECT term
                    FROM amplified_signals
                    WHERE recorded_at > datetime('now', ? || ' hours')
                    ORDER BY source_count DESC
                    """,
                    (f"-{hours}",),
                ).fetchall()

            return [r[0] for r in rows if r[0]]

        except sqlite3.OperationalError as exc:
            logger.debug("amplified_signals table not available: %s", exc)
            return []

    # ─── Private helpers ─────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create the amplified_signals table if it does not exist."""
        with sqlite3.connect(settings.generator_db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS amplified_signals (
                    term         TEXT PRIMARY KEY,
                    source_count INTEGER NOT NULL DEFAULT 1,
                    recorded_at  TEXT    NOT NULL
                )
                """
            )
            conn.commit()
