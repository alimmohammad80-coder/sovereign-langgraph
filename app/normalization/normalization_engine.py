from __future__ import annotations

from typing import Any

from app.normalization.base_normalizer import BaseNormalizer
from app.normalization.canonical_record import (
    CanonicalIntelligenceRecord,
)


class NormalizationEngine:
    def __init__(
        self,
        normalizers: list[BaseNormalizer] | None = None,
    ) -> None:
        self._normalizers: dict[str, BaseNormalizer] = {}

        for normalizer in normalizers or []:
            self.register(normalizer)

    def register(self, normalizer: BaseNormalizer) -> None:
        source_key = normalizer.source_key.strip().upper()

        if not source_key:
            raise ValueError("Normalizer source_key cannot be empty.")

        self._normalizers[source_key] = normalizer

    def available_sources(self) -> list[str]:
        return sorted(self._normalizers)

    def normalize(
        self,
        source_key: str,
        raw_record: dict[str, Any],
    ) -> CanonicalIntelligenceRecord:
        normalizer = self._normalizers.get(
            source_key.strip().upper()
        )

        if normalizer is None:
            raise KeyError(
                f"No normalizer registered for source: {source_key}"
            )

        return normalizer.normalize(raw_record)

    def normalize_many(
        self,
        source_key: str,
        raw_records: list[dict[str, Any]],
    ) -> tuple[
        list[CanonicalIntelligenceRecord],
        list[dict[str, Any]],
    ]:
        normalizer = self._normalizers.get(
            source_key.strip().upper()
        )

        if normalizer is None:
            raise KeyError(
                f"No normalizer registered for source: {source_key}"
            )

        return normalizer.normalize_many(raw_records)
