"""
GitHub connector — fetches trending repositories via GraphQL (authenticated)
or the public REST search API (unauthenticated fallback).

Trending criteria: stars > 500, pushed within last 7 days, topics include
ai / machine-learning / llm / mlops / distributed-systems / gpu /
edge-computing / cybersecurity.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx

from src.config import settings
from src.connectors.base import BaseConnector
from src.retry import with_backoff
from src.schemas import DataSource, RawDocument

logger = logging.getLogger(__name__)

_GRAPHQL_URL = "https://api.github.com/graphql"
_REST_URL = "https://api.github.com/search/repositories"

_TOPICS = [
    "ai",
    "machine-learning",
    "llm",
    "mlops",
    "distributed-systems",
    "gpu",
    "edge-computing",
    "cybersecurity",
]

_GRAPHQL_QUERY = """
query TrendingRepos($query: String!, $first: Int!) {
  search(query: $query, type: REPOSITORY, first: $first) {
    nodes {
      ... on Repository {
        nameWithOwner
        description
        url
        stargazerCount
        pushedAt
        repositoryTopics(first: 10) {
          nodes {
            topic { name }
          }
        }
        defaultBranchRef {
          name
        }
        object(expression: "HEAD:README.md") {
          ... on Blob {
            text
          }
        }
      }
    }
  }
}
"""


def _build_graphql_query_str() -> str:
    week_ago = (datetime.now(tz=UTC) - timedelta(days=7)).strftime("%Y-%m-%d")
    topic_part = " ".join(f"topic:{t}" for t in _TOPICS)
    return f"{topic_part} stars:>500 pushed:>{week_ago}"


def _extract_body(repo: dict) -> str:
    """Extract README excerpt or fall back to description + topics."""
    readme_node = repo.get("object")
    if readme_node and isinstance(readme_node, dict):
        text: str = readme_node.get("text") or ""
        if text.strip():
            return text[:2000]

    description: str = repo.get("description") or ""
    topics_nodes = (
        repo.get("repositoryTopics", {}).get("nodes") or []
    )
    topic_names = [n["topic"]["name"] for n in topics_nodes if n.get("topic")]
    parts = [description]
    if topic_names:
        parts.append("Topics: " + ", ".join(topic_names))
    return "\n".join(filter(None, parts))


class GithubConnector(BaseConnector):
    SOURCE_ID = "github"

    @with_backoff(max_retries=4, exceptions=(httpx.HTTPError, httpx.TimeoutException))
    async def fetch(self, *, max_results: int = 30) -> list[RawDocument]:
        if settings.github_token:
            return await self._fetch_graphql(max_results)
        return await self._fetch_rest(max_results)

    async def _fetch_graphql(self, max_results: int) -> list[RawDocument]:
        headers = {
            "Authorization": f"Bearer {settings.github_token}",
            "Content-Type": "application/json",
        }
        query_str = _build_graphql_query_str()
        payload = {
            "query": _GRAPHQL_QUERY,
            "variables": {"query": query_str, "first": min(max_results, 100)},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(_GRAPHQL_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        nodes = data.get("data", {}).get("search", {}).get("nodes", [])
        docs: list[RawDocument] = []
        for repo in nodes:
            if not repo:
                continue
            name_with_owner: str = repo.get("nameWithOwner", "")
            if not name_with_owner:
                continue

            body = _extract_body(repo)
            published_at: datetime | None = None
            pushed_raw = repo.get("pushedAt")
            if pushed_raw:
                try:
                    published_at = datetime.fromisoformat(pushed_raw.replace("Z", "+00:00"))
                except ValueError:
                    pass

            docs.append(
                RawDocument(
                    title=name_with_owner,
                    url=repo.get("url", f"https://github.com/{name_with_owner}"),
                    body=body,
                    author=name_with_owner.split("/")[0],
                    published_at=published_at,
                    source=DataSource.GITHUB,
                    source_id=name_with_owner,
                    extra={"stars": repo.get("stargazerCount", 0)},
                )
            )

        logger.info("GitHub GraphQL fetched %d repos", len(docs))
        return docs[:max_results]

    async def _fetch_rest(self, max_results: int) -> list[RawDocument]:
        topic_query = "+".join(f"topic:{t}" for t in _TOPICS[:4])  # REST URL-length cap
        params = {
            "q": topic_query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(max_results, 100),
        }
        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(_REST_URL, params=params, headers=headers)  # type: ignore[arg-type]
            response.raise_for_status()
            data = response.json()

        items: list[dict] = data.get("items", [])
        docs: list[RawDocument] = []
        for repo in items:
            full_name: str = repo.get("full_name", "")
            if not full_name:
                continue

            description: str = repo.get("description") or ""
            topics: list[str] = repo.get("topics") or []
            body_parts = [description]
            if topics:
                body_parts.append("Topics: " + ", ".join(topics))
            body = "\n".join(filter(None, body_parts))

            published_at = None
            pushed_raw = repo.get("pushed_at")
            if pushed_raw:
                try:
                    published_at = datetime.fromisoformat(pushed_raw.replace("Z", "+00:00"))
                except ValueError:
                    pass

            docs.append(
                RawDocument(
                    title=full_name,
                    url=repo.get("html_url", f"https://github.com/{full_name}"),
                    body=body,
                    author=repo.get("owner", {}).get("login"),
                    published_at=published_at,
                    source=DataSource.GITHUB,
                    source_id=full_name,
                    extra={"stars": repo.get("stargazers_count", 0)},
                )
            )

        logger.info("GitHub REST fallback fetched %d repos", len(docs))
        return docs[:max_results]
