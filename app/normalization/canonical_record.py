from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class CanonicalEntity(BaseModel):
    entity_type: str
    name: str
    canonical_name: str | None = None
    external_id: str | None = None
    country_iso3: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalLocation(BaseModel):
    country_iso3: str | None = None
    region_key: str | None = None
    place_name: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class CanonicalIntelligenceRecord(BaseModel):
    record_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    source_key: str
    source_record_id: str | None = None
    evidence_id: str | None = None

    record_type: str
    event_type: str | None = None
    title: str
    summary: str
    raw_text: str | None = None

    published_at: datetime | None = None
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    language_code: str = "en"
    location: CanonicalLocation = Field(
        default_factory=CanonicalLocation
    )
    entities: list[CanonicalEntity] = Field(
        default_factory=list
    )

    themes: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    commodities: list[str] = Field(default_factory=list)

    direction: str = "STABLE"
    severity: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_reliability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
    )

    canonical_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "source_key",
        "record_type",
        "direction",
        mode="before",
    )
    @classmethod
    def normalize_uppercase(cls, value: str) -> str:
        return str(value).strip().upper()

    @field_validator("language_code", mode="before")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return str(value or "en").strip().lower()

    @field_validator("themes", "sectors", "commodities")
    @classmethod
    def remove_duplicate_values(
        cls,
        values: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []

        for value in values:
            cleaned = str(value).strip()

            if not cleaned:
                continue

            key = cleaned.casefold()

            if key not in seen:
                seen.add(key)
                normalized.append(cleaned)

        return normalized
