from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConflictObservationCreate(BaseModel):
    observed_at: datetime

    source: str
    source_url: str | None = None
    source_version: str | None = None

    title: str | None = None
    summary: str | None = None

    country: str | None = None
    country_iso3: str | None = None

    related_state_iso3: list[str] = Field(
        default_factory=list
    )

    conflict_id: int | None = None

    event_type: str

    severity: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    observation_data: dict[str, Any] = Field(
        default_factory=dict
    )


class ConflictObservationResult(BaseModel):
    observation_key: str
    country_iso3: str | None = None
    conflict_id: int | None = None
    canonical_episode_id: str | None = None
    created: bool
