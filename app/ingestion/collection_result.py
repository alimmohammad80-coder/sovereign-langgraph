from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class CollectionResult:
    source_key: str
    success: bool
    records_collected: int = 0
    records_ingested: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None

    def complete(self) -> None:
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "success": self.success,
            "records_collected": self.records_collected,
            "records_ingested": self.records_ingested,
            "duplicates_skipped": self.duplicates_skipped,
            "errors": self.errors,
            "metadata": self.metadata,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
        }
