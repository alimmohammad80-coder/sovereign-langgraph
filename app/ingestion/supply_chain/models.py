from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class SupplyChainEvidence:
    source: str
    source_record_id: str
    evidence_type: str
    title: str
    summary: str = ""
    url: str | None = None
    published_at: str | None = None
    observed_at: str | None = None
    country_iso3: str | None = None
    matched_company: str | None = None
    matched_port: str | None = None
    matched_chokepoint: str | None = None
    matched_commodity: str | None = None
    matched_corridor: str | None = None
    event_type: str | None = None
    severity_score: float | None = None
    confidence_score: float | None = None
    metric_name: str | None = None
    metric_value: float | None = None
    metric_unit: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def content_hash(self) -> str:
        payload = {
            "source": self.source,
            "source_record_id": self.source_record_id,
            "title": self.title,
            "summary": self.summary,
            "published_at": self.published_at,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_storage_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["content_hash"] = self.content_hash()
        return row

    def to_live_event_row(self) -> dict[str, Any] | None:
        if self.evidence_type != "event":
            return None
        if not any(
            (
                self.matched_company,
                self.matched_port,
                self.matched_chokepoint,
                self.matched_commodity,
            )
        ):
            return None
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "event_type": self.event_type or "monitoring",
            "matched_port": self.matched_port,
            "matched_chokepoint": self.matched_chokepoint,
            "matched_commodity": self.matched_commodity,
            "matched_company": self.matched_company,
            "severity_score": self.severity_score or 50,
            "confidence_score": self.confidence_score or 60,
            "published_at": self.published_at,
            "ingested_at": self.ingested_at,
            "raw_payload": {
                "source_record_id": self.source_record_id,
                "country_iso3": self.country_iso3,
                "matched_corridor": self.matched_corridor,
                **self.raw_payload,
            },
        }
