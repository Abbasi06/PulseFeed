"""
Dev.to connector — fetches high-signal articles across ML/AI/DevOps/MLOps tags.

Runs 4 tag queries in parallel and merges results, filtering for
positive_reactions_count > 30.
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

_BASE_URL = "https://dev.to/api/articles"
_MIN_REACTIONS = 30
_TAGS = ["machinelearning", "devops", "ai", "mlops"]


class DevtoConnector(BaseConnector):
    SOURCE_ID = "devto"

    @with_backoff(max_retries=3, exceptions=(httpx.HTTPError,))
    async def fetch(self, *, max_results: int = 30) -> list[RawDocument]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            tasks = [self._fetch_tag(client, tag, max_results) for tag in _TAGS]
            results_nested: list[list[dict]] = await asyncio.gather(*tasks)

        # Deduplicate by article id, filter by reaction threshold
        seen_ids: set[str] = set()
        filtered: list[dict] = []
        for batch in results_nested:
            for article in batch:
                article_id = str(article.get("id", ""))
                if not article_id or article_id in seen_ids:
                    continue
                reactions: int = article.get("positive_reactions_count") or 0
                if reactions <= _MIN_REACTIONS:
                    continue
                seen_ids.add(article_id)
                filtered.append(article)

        # Sort by reactions descending for highest-signal first
        filtered.sort(key=lambda a: a.get("positive_reactions_count") or 0, reverse=True)

        docs: list[RawDocument] = []
        for article in filtered[:max_results]:
            doc = self._to_raw_document(article)
            if doc is not None:
                docs.append(doc)

        logger.info("Dev.to fetched %d articles", len(docs))
        return docs

    async def _fetch_tag(
        self, client: httpx.AsyncClient, tag: str, max_results: int
    ) -> list[dict]:
        params: dict[str, str | int] = {
            "per_page": max_results,
            "top": 7,
            "tag": tag,
        }
        try:
            response = await client.get(_BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("Dev.to tag=%r fetch failed: %s", tag, exc)
            return []

    def _to_raw_document(self, article: dict) -> RawDocument | None:
        article_id = str(article.get("id", ""))
        title: str = article.get("title") or ""
        url: str = article.get("url") or ""

        if not title or not url:
            return None

        body: str = (
            article.get("body_markdown")
            or article.get("description")
            or ""
        )

        author: str | None = None
        user: dict = article.get("user") or {}
        author = user.get("name") or user.get("username")

        published_at: datetime | None = None
        pub_raw: str | None = article.get("published_at")
        if pub_raw:
            try:
                published_at = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
            except ValueError:
                pass

        tags: list[str] = article.get("tag_list") or []
        reactions: int = article.get("positive_reactions_count") or 0

        return RawDocument(
            title=title,
            url=url,
            body=body,
            author=author,
            published_at=published_at,
            source=DataSource.DEVTO,
            source_id=article_id,
            extra={"positive_reactions_count": reactions, "tags": tags},
        )
