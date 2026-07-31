from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.ingestion.collection_result import CollectionResult


class BaseCollector(ABC):
    source_key: str

    @abstractmethod
    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        """
        Collect source records and return normalized raw-ingestion payloads.

        Each record should be compatible with the SEWS evidence ingestion
        service or the future shared evidence ingestion service.
        """
        raise NotImplementedError
