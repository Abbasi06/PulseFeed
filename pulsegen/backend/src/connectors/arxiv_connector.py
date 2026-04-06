"""
arXiv connector — fetches recent papers across AI/ML/systems categories.

Uses the `arxiv` Python library with thread-pool execution to avoid blocking
the async event loop. All category+query combos run in parallel via
asyncio.gather.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC

import arxiv  # type: ignore[import-untyped,unused-ignore]

from src.connectors.base import BaseConnector
from src.retry import with_backoff
from src.schemas import DataSource, RawDocument

logger = logging.getLogger(__name__)

# Each tuple: (categories list, query string)
_SEARCH_SPECS: list[tuple[list[str], str]] = [
    (["cs.AI", "cs.LG"], "large language model inference optimization"),
    (["cs.AI", "cs.LG"], "transformer architecture efficiency"),
    (["cs.DC"], "distributed systems consensus fault tolerance"),
    (["cs.AR"], "GPU hardware accelerator ML workload"),
    (["cs.LG"], "federated learning privacy differential"),
    (["cs.AI"], "agentic AI planning tool use reasoning"),
    (["cs.LG"], "MLOps monitoring observability production"),
    (["cs.DC"], "edge computing deployment embedded inference"),
]

_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="arxiv-worker")


def _category_filter(categories: list[str]) -> str:
    """Build arXiv category filter string."""
    return " OR ".join(f"cat:{c}" for c in categories)


def _blocking_search(categories: list[str], query: str, max_results: int) -> list[arxiv.Result]:
    """Run a synchronous arXiv search. Intended to run in a thread executor."""
    cat_filter = _category_filter(categories)
    full_query = f"({cat_filter}) AND ({query})"
    search = arxiv.Search(
        query=full_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    client = arxiv.Client(num_retries=2, delay_seconds=1.0)
    return list(client.results(search))


class ArxivConnector(BaseConnector):
    SOURCE_ID = "arxiv"

    @with_backoff(max_retries=4, exceptions=(Exception,))
    async def fetch(self, *, max_results: int = 30) -> list[RawDocument]:
        """
        Run all search specs in parallel and return deduplicated RawDocuments.
        """
        per_spec = max(4, max_results // len(_SEARCH_SPECS))
        loop = asyncio.get_running_loop()

        async def _fetch_one(categories: list[str], query: str) -> list[arxiv.Result]:
            try:
                return await loop.run_in_executor(
                    _EXECUTOR, _blocking_search, categories, query, per_spec
                )
            except Exception as exc:
                logger.warning(
                    "arXiv search failed for query=%r categories=%r: %s",
                    query,
                    categories,
                    exc,
                )
                return []

        tasks = [_fetch_one(cats, q) for cats, q in _SEARCH_SPECS]
        results_nested: list[list[arxiv.Result]] = await asyncio.gather(*tasks)

        seen_ids: set[str] = set()
        docs: list[RawDocument] = []

        for results in results_nested:
            for paper in results:
                paper_id: str = paper.get_short_id()
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)

                first_author: str | None = None
                if paper.authors:
                    first_author = paper.authors[0].name

                published_at = None
                if paper.published is not None:
                    published_at = paper.published.replace(tzinfo=UTC)

                docs.append(
                    RawDocument(
                        title=paper.title.strip(),
                        url=paper.entry_id,
                        body=paper.summary.strip(),
                        author=first_author,
                        published_at=published_at,
                        source=DataSource.ARXIV,
                        source_id=paper_id,
                        extra={
                            "categories": paper.categories,
                            "doi": paper.doi,
                            "pdf_url": paper.pdf_url,
                        },
                    )
                )
                if len(docs) >= max_results:
                    break
            if len(docs) >= max_results:
                break

        logger.info("arXiv fetched %d unique papers", len(docs))
        return docs[:max_results]
