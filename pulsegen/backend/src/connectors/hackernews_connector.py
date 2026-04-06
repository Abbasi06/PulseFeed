"""
Hacker News connector — fetches top stories via the Algolia HN search API.

Runs two searches in parallel (general top stories + AI/ML query), then
enriches each story body with the top 3 comments.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from src.connectors.base import BaseConnector
from src.retry import with_backoff
from src.schemas import DataSource, RawDocument

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
_ITEMS_URL = "https://hn.algolia.com/api/v1/items/{object_id}"

_QUERIES = ["", "AI ML engineering"]


class HackernewsConnector(BaseConnector):
    SOURCE_ID = "hackernews"

    @with_backoff(max_retries=3, exceptions=(httpx.HTTPError,))
    async def fetch(self, *, max_results: int = 30) -> list[RawDocument]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            search_tasks = [self._search(client, q, max_results) for q in _QUERIES]
            results_nested: list[list[dict]] = await asyncio.gather(*search_tasks)

        # Deduplicate by objectID, keeping first occurrence
        seen_ids: set[str] = set()
        hits: list[dict] = []
        for batch in results_nested:
            for hit in batch:
                oid = str(hit.get("objectID", ""))
                url = hit.get("url", "")
                if not oid or not url:
                    continue
                if oid in seen_ids:
                    continue
                seen_ids.add(oid)
                hits.append(hit)

        hits = hits[:max_results]

        # Enrich each story with top-3 comment text
        async with httpx.AsyncClient(timeout=20.0) as client:
            enrich_tasks = [self._enrich_story(client, hit) for hit in hits]
            docs: list[RawDocument | None] = await asyncio.gather(*enrich_tasks)

        result = [d for d in docs if d is not None]
        logger.info("HackerNews fetched %d stories", len(result))
        return result

    async def _search(
        self, client: httpx.AsyncClient, query: str, max_results: int
    ) -> list[dict]:
        params: dict[str, str | int] = {
            "tags": "story",
            "numericFilters": "points>100",
            "hitsPerPage": max_results,
            "query": query,
        }
        try:
            response = await client.get(_SEARCH_URL, params=params)
            response.raise_for_status()
            return response.json().get("hits", [])  # type: ignore[no-any-return]
        except httpx.HTTPError as exc:
            logger.warning("HN search failed for query=%r: %s", query, exc)
            return []

    async def _enrich_story(
        self, client: httpx.AsyncClient, hit: dict
    ) -> RawDocument | None:
        object_id = str(hit.get("objectID", ""))
        title: str = hit.get("title") or ""
        url: str = hit.get("url") or ""
        points: int = hit.get("points") or 0
        author: str | None = hit.get("author")

        body_parts = [title, url]

        try:
            item_url = _ITEMS_URL.format(object_id=object_id)
            response = await client.get(item_url)
            response.raise_for_status()
            item_data = response.json()
            children: list[dict] = item_data.get("children") or []
            comment_texts: list[str] = []
            for child in children[:3]:
                text: str = child.get("text") or ""
                if text.strip():
                    comment_texts.append(text.strip())
            if comment_texts:
                body_parts.append("\n\n" + "\n\n".join(comment_texts))
        except httpx.HTTPError as exc:
            logger.warning("HN item fetch failed for id=%s: %s", object_id, exc)

        published_at = None
        created_at_raw = hit.get("created_at")
        if created_at_raw:
            from datetime import datetime

            try:
                published_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except ValueError:
                pass

        return RawDocument(
            title=title,
            url=url,
            body="\n\n".join(filter(None, body_parts)),
            author=author,
            published_at=published_at,
            source=DataSource.HACKERNEWS,
            source_id=object_id,
            extra={"points": points},
        )
