"""
Abstract base class for all source connectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.schemas import RawDocument


class BaseConnector(ABC):
    SOURCE_ID: str

    @abstractmethod
    async def fetch(self, *, max_results: int = 30) -> list[RawDocument]:
        """Fetch raw documents from the source. Must be implemented by subclasses."""
        ...

    def source_label(self) -> str:
        return self.SOURCE_ID
