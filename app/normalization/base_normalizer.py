from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.normalization.canonical_record import (
    CanonicalIntelligenceRecord,
)


class BaseNormalizer(ABC):
    source_key: str

    @abstractmethod
    def normalize(
        self,
        raw_record: dict[str, Any],
    ) -> CanonicalIntelligenceRecord:
        """
        Convert a source-specific record into the platform's canonical
        intelligence format.
        """
        raise NotImplementedError

    def normalize_many(
        self,
        raw_records: list[dict[str, Any]],
    ) -> tuple[
        list[CanonicalIntelligenceRecord],
        list[dict[str, Any]],
    ]:
        normalized: list[CanonicalIntelligenceRecord] = []
        errors: list[dict[str, Any]] = []

        for index, raw_record in enumerate(raw_records):
            try:
                normalized.append(self.normalize(raw_record))
            except Exception as exc:
                errors.append(
                    {
                        "index": index,
                        "source_key": self.source_key,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )

        return normalized, errors
