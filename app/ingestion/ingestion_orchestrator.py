from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.ingestion.base_collector import BaseCollector
from app.ingestion.collection_result import CollectionResult

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    def __init__(
        self,
        collectors: list[BaseCollector] | None = None,
    ) -> None:
        self._collectors: dict[str, BaseCollector] = {}

        for collector in collectors or []:
            self.register(collector)

    def register(self, collector: BaseCollector) -> None:
        if not collector.source_key:
            raise ValueError("Collector source_key cannot be empty.")

        self._collectors[collector.source_key.upper()] = collector

    def available_sources(self) -> list[str]:
        return sorted(self._collectors)

    async def run_source(
        self,
        source_key: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        collector = self._collectors.get(source_key.upper())

        if collector is None:
            raise KeyError(f"Unknown collector source: {source_key}")

        try:
            records, result = await collector.collect(context or {})
            result.complete()
            return records, result

        except Exception as exc:
            logger.exception(
                "Collector failed for source %s",
                source_key,
            )

            result = CollectionResult(
                source_key=source_key.upper(),
                success=False,
                errors=[f"{type(exc).__name__}: {exc}"],
            )
            result.complete()

            return [], result

    async def run_all(
        self,
        context: dict[str, Any] | None = None,
    ) -> dict[str, tuple[list[dict[str, Any]], CollectionResult]]:
        tasks = {
            source_key: asyncio.create_task(
                self.run_source(source_key, context)
            )
            for source_key in self.available_sources()
        }

        results: dict[
            str,
            tuple[list[dict[str, Any]], CollectionResult],
        ] = {}

        for source_key, task in tasks.items():
            results[source_key] = await task

        return results
