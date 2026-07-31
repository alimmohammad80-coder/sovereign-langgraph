from __future__ import annotations

from typing import Any

from app.ingestion.base_collector import BaseCollector
from app.ingestion.collection_result import CollectionResult


class GDELTCollector(BaseCollector):
    source_key = "GDELT"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}

        result = CollectionResult(
            source_key=self.source_key,
            success=True,
            metadata={
                "query": context.get("query"),
                "country_iso3": context.get("country_iso3"),
            },
        )

        # Live GDELT retrieval will be implemented next.
        records: list[dict[str, Any]] = []

        result.records_collected = len(records)
        return records, result
