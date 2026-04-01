"""
HuggingFace connector — fetches papers from the HF Daily Papers feed
and the top-upvoted papers endpoint, then merges and deduplicates.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import httpx

from src.connectors.base import BaseConnector
from src.retry import with_backoff
from src.schemas import DataSource, RawDocument

logger = logging.getLogger(__name__)

_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"
_TOP_PAPERS_URL = "https://huggingface.co/api/papers"


def _parse_hf_paper(paper: dict) -> RawDocument | None:
    """Convert a raw HF paper dict to a RawDocument."""
    paper_data: dict = paper.get("paper") or paper  # daily_papers wraps in {"paper": {...}}

    arxiv_id: str = paper_data.get("id") or ""
    title: str = paper_data.get("title") or ""
    abstract: str = paper_data.get("abstract") or ""

    if not arxiv_id or not title:
        return None

    url = f"https://arxiv.org/abs/{arxiv_id}"

    authors: list[dict] = paper_data.get("authors") or []
    first_author: str | None = None
    if authors:
        first_author = authors[0].get("name")

    published_at: datetime | None = None
    pub_raw: str | None = paper_data.get("publishedAt") or paper_data.get("published_at")
    if pub_raw:
        try:
            published_at = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
        except ValueError:
            pass

    upvotes: int = paper.get("upvotes") or paper_data.get("upvotes") or 0

    return RawDocument(
        title=title,
        url=url,
        body=abstract,
        author=first_author,
        published_at=published_at,
        source=DataSource.HUGGINGFACE,
        source_id=arxiv_id,
        extra={"upvotes": upvotes, "hf_paper_id": arxiv_id},
    )


class HuggingfaceConnector(BaseConnector):
    SOURCE_ID = "huggingface"

    @with_backoff(max_retries=3, exceptions=(httpx.HTTPError,))
    async def fetch(self, *, max_results: int = 30) -> list[RawDocument]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            daily_task = self._fetch_daily(client)
            top_task = self._fetch_top(client, max_results)
            daily_papers, top_papers = await asyncio.gather(daily_task, top_task)

        # Merge: daily papers first, then top; deduplicate by arxiv id
        seen_ids: set[str] = set()
        docs: list[RawDocument] = []

        for doc in daily_papers + top_papers:
            if doc.source_id and doc.source_id in seen_ids:
                continue
            if doc.source_id:
                seen_ids.add(doc.source_id)
            docs.append(doc)
            if len(docs) >= max_results:
                break

        logger.info("HuggingFace fetched %d papers", len(docs))
        return docs

    async def _fetch_daily(self, client: httpx.AsyncClient) -> list[RawDocument]:
        try:
            response = await client.get(_DAILY_PAPERS_URL)
            response.raise_for_status()
            papers: list[dict] = response.json()
        except httpx.HTTPError as exc:
            logger.warning("HuggingFace daily papers fetch failed: %s", exc)
            return []

        docs: list[RawDocument] = []
        for paper in papers:
            doc = _parse_hf_paper(paper)
            if doc is not None:
                docs.append(doc)
        return docs

    async def _fetch_top(self, client: httpx.AsyncClient, max_results: int) -> list[RawDocument]:
        try:
            response = await client.get(
                _TOP_PAPERS_URL, params={"limit": max_results, "sort": "upvotes"}
            )
            response.raise_for_status()
            papers: list[dict] = response.json()
        except httpx.HTTPError as exc:
            logger.warning("HuggingFace top papers fetch failed: %s", exc)
            return []

        docs: list[RawDocument] = []
        for paper in papers:
            doc = _parse_hf_paper(paper)
            if doc is not None:
                docs.append(doc)
        return docs
