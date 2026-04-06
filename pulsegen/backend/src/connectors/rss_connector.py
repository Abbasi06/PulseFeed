"""
RSS connector — fetches from 30+ curated RSS feeds spanning AI research labs,
cloud engineering blogs, ML newsletters, expert practitioners, and community
aggregators.

All feeds are fetched in parallel. Failed feeds are skipped with a warning.
Results are sorted: tier-1 sources first, then by published_at descending.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

import feedparser
import httpx
from dateutil import parser as dateutil_parser  # type: ignore[import-untyped,unused-ignore]

from src.connectors.base import BaseConnector
from src.retry import with_backoff
from src.schemas import DataSource, RawDocument

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub(" ", text).strip()


@dataclass(frozen=True)
class RSSSource:
    source_id: str
    label: str
    url: str
    tier: int  # 1 = highest signal, 2 = good signal


RSS_SOURCES: list[RSSSource] = [
    # ── Tier 1 — AI Research Labs ────────────────────────────────────────────
    RSSSource("google_ai_blog", "Google AI Blog", "https://blog.google/technology/ai/rss/", 1),
    RSSSource("deepmind", "DeepMind Blog", "https://deepmind.google/discover/blog/rss.xml", 1),
    RSSSource("anthropic", "Anthropic Research", "https://www.anthropic.com/rss.xml", 1),
    RSSSource("openai_blog", "OpenAI Blog", "https://openai.com/news/rss.xml", 1),
    RSSSource("meta_ai", "Meta AI Blog", "https://ai.meta.com/blog/rss.xml", 1),
    # ── Tier 1 — Cloud & Infrastructure ─────────────────────────────────────
    RSSSource("aws_ml", "AWS ML Blog", "https://aws.amazon.com/blogs/machine-learning/feed/", 1),
    RSSSource("cloudflare_blog", "Cloudflare Blog", "https://blog.cloudflare.com/rss/", 1),
    RSSSource("netflix_tech", "Netflix TechBlog", "https://netflixtechblog.com/feed", 1),
    RSSSource("uber_eng", "Uber Engineering", "https://www.uber.com/en-US/blog/engineering/rss/", 1),
    # ── Tier 1 — Academic / Research Aggregators ────────────────────────────
    RSSSource("papers_with_code", "Papers With Code", "https://paperswithcode.com/latest/rss", 1),
    RSSSource("the_gradient", "The Gradient", "https://thegradient.pub/rss/", 1),
    # ── Tier 2 — Expert Practitioners ───────────────────────────────────────
    RSSSource("chip_huyen", "Chip Huyen", "https://huyenchip.com/feed.xml", 2),
    RSSSource("lil_log", "Lil'Log (Lilian Weng)", "https://lilianweng.github.io/feed.xml", 2),
    RSSSource("sebastian_ruder", "Sebastian Ruder NLP", "https://ruder.io/rss/index.rss", 2),
    RSSSource("eugene_yan", "Eugene Yan", "https://eugeneyan.com/feed.xml", 2),
    RSSSource("jay_alammar", "Jay Alammar", "https://jalammar.github.io/feed.xml", 2),
    RSSSource("andrej_karpathy", "Andrej Karpathy", "https://karpathy.github.io/feed.xml", 2),
    # ── Tier 2 — Newsletters ─────────────────────────────────────────────────
    RSSSource("import_ai", "Import AI (Jack Clark)", "https://jack-clark.net/feed/", 2),
    RSSSource("the_sequence", "The Sequence", "https://thesequence.substack.com/feed", 2),
    RSSSource("mlops_community", "MLOps Community", "https://mlops.community/feed/", 2),
    RSSSource("data_elixir", "Data Elixir", "https://dataelixir.com/issues/rss/", 2),
    RSSSource("towards_ai", "Towards AI", "https://towardsai.net/feed", 2),
    # ── Tier 2 — Community Aggregators ──────────────────────────────────────
    RSSSource("lobsters_ai", "Lobste.rs/AI", "https://lobste.rs/t/ai.rss", 2),
    RSSSource("lobsters_ml", "Lobste.rs/ML", "https://lobste.rs/t/ml.rss", 2),
    RSSSource("lobsters_distributed", "Lobste.rs/Distributed", "https://lobste.rs/t/distributed.rss", 2),
    # ── Tier 2 — Enterprise Engineering Blogs ───────────────────────────────
    RSSSource("shopify_eng", "Shopify Engineering", "https://shopify.engineering/articles.rss", 2),
    RSSSource("doordash_eng", "DoorDash Engineering", "https://doordash.engineering/feed/", 2),
    RSSSource("airbnb_eng", "Airbnb Engineering", "https://medium.com/feed/airbnb-engineering", 2),
    RSSSource("stripe_blog", "Stripe Engineering", "https://stripe.com/blog/engineering/feed/rss", 2),
    RSSSource("discord_eng", "Discord Engineering", "https://discord.com/blog/engineering/rss", 2),
    # ── Tier 2 — GPU / Hardware ──────────────────────────────────────────────
    RSSSource("nvidia_dev", "NVIDIA Developer Blog", "https://developer.nvidia.com/blog/feed/", 2),
    RSSSource("hpc_wire", "HPCwire", "https://www.hpcwire.com/feed/", 2),
]


def _parse_published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    raw: str | None = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not raw:
        return None
    try:
        result: datetime = dateutil_parser.parse(raw, ignoretz=False)
        return result
    except (ValueError, OverflowError, TypeError):
        return None


def _extract_body(entry: feedparser.FeedParserDict) -> str:
    # Prefer full content over summary
    content_list = getattr(entry, "content", None)
    if content_list:
        raw = content_list[0].get("value", "")
        if raw:
            return _strip_html(raw)
    summary = getattr(entry, "summary", None)
    if summary:
        return _strip_html(summary)
    return ""


def _extract_author(entry: feedparser.FeedParserDict, feed: feedparser.FeedParserDict) -> str | None:
    author: str | None = getattr(entry, "author", None)
    if author:
        return author
    feed_author: str | None = getattr(feed.feed, "author", None)
    return feed_author or None


def _entries_to_docs(
    rss_source: RSSSource, feed: feedparser.FeedParserDict
) -> list[RawDocument]:
    docs: list[RawDocument] = []
    for entry in feed.entries:
        link: str = getattr(entry, "link", "") or ""
        title: str = getattr(entry, "title", "") or ""
        if not link or not title:
            continue

        body = _extract_body(entry)
        author = _extract_author(entry, feed)
        published_at = _parse_published_at(entry)
        source_id = f"{rss_source.source_id}:{link}"

        docs.append(
            RawDocument(
                title=title.strip(),
                url=link,
                body=body,
                author=author,
                published_at=published_at,
                source=DataSource.RSS,
                source_id=source_id,
                extra={
                    "rss_source": rss_source.label,
                    "tier": rss_source.tier,
                },
            )
        )
    return docs


async def _fetch_one_feed(
    client: httpx.AsyncClient, rss_source: RSSSource
) -> list[RawDocument]:
    try:
        response = await client.get(rss_source.url, follow_redirects=True)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        docs = _entries_to_docs(rss_source, feed)
        logger.debug("RSS %s: fetched %d entries", rss_source.source_id, len(docs))
        return docs
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("RSS feed %s (%s) failed: %s", rss_source.source_id, rss_source.url, exc)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "RSS feed %s unexpected error: %s: %s",
            rss_source.source_id,
            type(exc).__name__,
            exc,
        )
        return []


class RSSConnector(BaseConnector):
    SOURCE_ID = "rss"

    @with_backoff(max_retries=3, exceptions=(httpx.HTTPError,))
    async def fetch(self, *, max_results: int = 30) -> list[RawDocument]:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=5.0),
            headers={"User-Agent": "PulseGen/1.0 RSS Harvester (+https://github.com/pulseboard)"},
        ) as client:
            tasks = [_fetch_one_feed(client, src) for src in RSS_SOURCES]
            results_nested: list[list[RawDocument]] = await asyncio.gather(*tasks)

        all_docs: list[RawDocument] = []
        for batch in results_nested:
            all_docs.extend(batch)

        # Sort: tier-1 first, then by published_at descending (newest first).
        # All timestamps are normalised to UTC-naive before comparison so that
        # mixed tz-aware / tz-naive values (common across RSS feeds) do not
        # produce incorrect orderings via .timestamp() local-time assumptions.
        _epoch = datetime.min.replace(tzinfo=None)

        def sort_key(doc: RawDocument) -> tuple[int, datetime]:
            tier: int = doc.extra.get("tier", 2)
            pub = doc.published_at or _epoch
            if pub.tzinfo is not None:
                pub = pub.astimezone(UTC).replace(tzinfo=None)
            return (tier, pub)

        all_docs.sort(key=sort_key, reverse=True)
        # reverse=True gives published_at DESC within each tier but also puts
        # tier=2 before tier=1.  Re-stable-sort on tier alone to restore tier
        # ordering while keeping published_at DESC within each tier bucket.
        all_docs.sort(key=lambda d: d.extra.get("tier", 2))

        logger.info("RSS connector fetched %d total docs across %d feeds", len(all_docs), len(RSS_SOURCES))
        return all_docs[:max_results]
