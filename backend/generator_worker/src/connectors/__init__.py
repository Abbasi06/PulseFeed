"""
Connector registry for the PulseGen ingestion pipeline.

CONNECTOR_REGISTRY maps source_id strings to instantiated connector objects.
Import this dict to iterate over all available connectors.
"""

from __future__ import annotations

from src.connectors.arxiv_connector import ArxivConnector
from src.connectors.base import BaseConnector
from src.connectors.devto_connector import DevtoConnector
from src.connectors.github_connector import GithubConnector
from src.connectors.hackernews_connector import HackernewsConnector
from src.connectors.huggingface_connector import HuggingfaceConnector
from src.connectors.rss_connector import RSSConnector

CONNECTOR_REGISTRY: dict[str, BaseConnector] = {
    ArxivConnector.SOURCE_ID: ArxivConnector(),
    GithubConnector.SOURCE_ID: GithubConnector(),
    HackernewsConnector.SOURCE_ID: HackernewsConnector(),
    HuggingfaceConnector.SOURCE_ID: HuggingfaceConnector(),
    DevtoConnector.SOURCE_ID: DevtoConnector(),
    RSSConnector.SOURCE_ID: RSSConnector(),
}

__all__ = [
    "CONNECTOR_REGISTRY",
    "BaseConnector",
    "ArxivConnector",
    "GithubConnector",
    "HackernewsConnector",
    "HuggingfaceConnector",
    "DevtoConnector",
    "RSSConnector",
]
