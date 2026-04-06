"""
Tests for DynamicQueryEngine.build_queries() — query blending, deduplication,
cap enforcement, and ArXiv extras.
SQLite is redirected to a temp file via tmp_db fixture.
"""

from unittest.mock import patch

from src.schemas import TAXONOMY_TAGS
from src.swarm.query_engine import (
    TAXONOMY_ANCHORS,
    DynamicQueryEngine,
)


def _engine(db_path: str) -> DynamicQueryEngine:
    with patch("src.swarm.query_engine.settings") as ms:
        ms.generator_db_path = db_path
        eng = DynamicQueryEngine()
    return eng


class TestDynamicQueryEngine:
    def test_returns_adaptive_query_set(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(source_id="github", hot_tags=[])
        from src.schemas import AdaptiveQuerySet
        assert isinstance(result, AdaptiveQuerySet)

    def test_queries_not_empty(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(source_id="github", hot_tags=[])
        assert len(result.queries) > 0

    def test_respects_max_queries_cap(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(source_id="github", hot_tags=["AI Engineering"], max_queries=5)
        assert len(result.queries) <= 5

    def test_no_duplicate_queries(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(
                source_id="github",
                hot_tags=["AI Engineering", "MLOps"],
            )
        lowered = [q.lower().strip() for q in result.queries]
        assert len(lowered) == len(set(lowered))

    def test_hot_tags_appear_in_hot_topics(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        hot = ["AI Engineering", "GPU Optimization"]
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(source_id="github", hot_tags=hot)
        assert set(hot) == set(result.hot_topics)

    def test_arxiv_source_gets_extra_queries(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        hot = ["AI Engineering"]
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result_arxiv = eng.build_queries(source_id="arxiv", hot_tags=hot, max_queries=50)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result_github = eng.build_queries(source_id="github", hot_tags=hot, max_queries=50)
        # ArXiv queries should be at least as many (due to extras)
        assert result_arxiv.base_queries_count >= result_github.base_queries_count

    def test_all_taxonomy_tags_covered_when_no_hot_tags(self, tmp_db: str) -> None:
        """With no hot tags, cold-path selects anchors for every tag."""
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(source_id="devto", hot_tags=[], max_queries=100)
        # At least one anchor per tag with anchors defined
        tags_with_anchors = [t for t in TAXONOMY_TAGS if t in TAXONOMY_ANCHORS]
        # We expect queries to cover content from most tags
        assert len(result.queries) >= len(tags_with_anchors)

    def test_amplified_signals_injected_into_queries(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        signals = ["Flash Attention Three", "vLLM Serving Scale"]
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(
                source_id="github",
                hot_tags=[],
                amplified_signals=signals,
                max_queries=50,
            )
        # At least one amplified signal should appear in queries
        assert any(sig in result.queries for sig in signals)

    def test_base_queries_count_non_negative(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(source_id="rss", hot_tags=[])
        assert result.base_queries_count >= 0
        assert result.trend_queries_count >= 0

    def test_source_id_preserved_in_result(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            result = eng.build_queries(source_id="hackernews", hot_tags=[])
        assert result.source_id == "hackernews"

    def test_no_anchors_tag_skipped_gracefully(self, tmp_db: str) -> None:
        """Tags not in TAXONOMY_ANCHORS are skipped without raising."""
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            # "UnknownTag" has no anchors — should not raise
            result = eng.build_queries(source_id="github", hot_tags=["UnknownTag"])
        assert isinstance(result.queries, list)

    def test_blend_with_trends_returns_anchor_plus_variants(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        anchor = "LLM inference serving"
        trending = ["Mamba SSM", "Flash Attention"]
        result = eng._blend_with_trends(anchor, trending, max_blend=2)
        assert result[0] == anchor
        assert len(result) >= 1

    def test_blend_with_empty_trending_returns_only_anchor(self, tmp_db: str) -> None:
        eng = _engine(tmp_db)
        result = eng._blend_with_trends("some anchor", [], max_blend=3)
        assert result == ["some anchor"]

    def test_load_trending_terms_returns_empty_when_table_missing(self, tmp_db: str) -> None:
        """Fresh DB has no trend_keywords table — should return [] gracefully."""
        eng = _engine(tmp_db)
        with patch("src.swarm.query_engine.settings") as ms:
            ms.generator_db_path = tmp_db
            terms = eng._load_trending_terms()
        assert terms == []
