from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import arxiv
import feedparser
import httpx

logger = logging.getLogger(__name__)

TOOLS_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "search",
        "description": "Search arxiv, GitHub, or RSS feeds for relevant content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "source": {"type": "string", "enum": ["arxiv", "github", "rss"]},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            "required": ["query", "source"],
        },
    }
]


def _search_arxiv(query: str, max_results: int) -> list[dict[str, str]]:
    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results)
    items: list[dict[str, str]] = []
    for result in client.results(search):
        items.append(
            {
                "title": result.title,
                "url": str(result.entry_id),
                "body": result.summary,
                "author": ", ".join(str(a) for a in result.authors[:3]),
                "published_at": result.published.isoformat(),
                "source": "arxiv",
            }
        )
    return items


def _search_github(query: str, max_results: int) -> list[dict[str, str]]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = httpx.get(
        "https://api.github.com/search/repositories",
        params={"q": query, "sort": "stars", "order": "desc", "per_page": max_results},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    items: list[dict[str, str]] = []
    for item in resp.json().get("items", []):
        desc = (item.get("description") or "") + " " + item.get("language", "")
        items.append(
            {
                "title": item["full_name"],
                "url": item["html_url"],
                "body": desc.strip(),
                "author": item.get("owner", {}).get("login", "Unknown"),
                "published_at": item.get("updated_at", ""),
                "source": "github",
            }
        )
    return items


def _search_rss(query: str, max_results: int) -> list[dict[str, str]]:
    # query format: "feeds:<url1>,<url2> keyword:<term>"
    feed_urls_str, _, keyword = query.partition(" keyword:")
    feed_urls_str = feed_urls_str.removeprefix("feeds:")
    feed_urls = [u.strip() for u in feed_urls_str.split(",") if u.strip()]
    keyword_lower = keyword.strip().lower()

    items: list[dict[str, str]] = []
    for url in feed_urls:
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            title: str = entry.get("title", "")
            summary: str = entry.get("summary", "")
            if keyword_lower and keyword_lower not in title.lower() and keyword_lower not in summary.lower():
                continue
            items.append(
                {
                    "title": title,
                    "url": entry.get("link", ""),
                    "body": summary,
                    "author": entry.get("author", "Unknown"),
                    "published_at": entry.get("published", ""),
                    "source": "rss",
                }
            )
            if len(items) >= max_results:
                return items
    return items


def _tool_search(arguments: dict[str, Any]) -> dict[str, Any]:
    query: str = arguments["query"]
    source: str = arguments["source"]
    max_results: int = min(max(int(arguments.get("max_results", 10)), 1), 50)

    try:
        if source == "arxiv":
            items = _search_arxiv(query, max_results)
        elif source == "github":
            items = _search_github(query, max_results)
        elif source == "rss":
            items = _search_rss(query, max_results)
        else:
            return {"items": []}
    except Exception as exc:
        logger.error("search failed for source=%s: %s", source, exc)
        return {"items": []}

    return {"items": items}


def _handle_tools_list(request_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS_MANIFEST}}


def _handle_tools_call(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name: str = params.get("name", "")
    arguments: dict[str, Any] = params.get("arguments", {})

    if name == "search":
        result = _tool_search(arguments)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Unknown tool: {name}"},
    }


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    method: str = request.get("method", "")
    params: dict[str, Any] = request.get("params", {})

    if method == "tools/list":
        return _handle_tools_list(request_id)
    if method == "tools/call":
        return _handle_tools_call(request_id, params)

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logger.info("search server started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
