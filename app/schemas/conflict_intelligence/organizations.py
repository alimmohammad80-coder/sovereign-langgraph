from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from .common import (
    ConfidenceGrade,
    RegistryRecord,
    ReviewStatus,
)


class NonStateOrganization(RegistryRecord):
    organization_id: str
    name: str
    aliases: list[str] = []

    active: bool = True

    areas_of_operation_iso3: list[str] = []
    territory_refs: list[str] = []

    estimated_strength: int | None = Field(
        default=None,
        ge=0,
    )

    headquarters_location: str | None = None
    external_ids: dict[str, str] = {}

    source: str
    source_url: str | None = None
    source_version: str | None = None

    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None


class GoverningAuthority(RegistryRecord):
    relationship_id: str

    organization_id: str

    state_iso3: str | None = None
    territory_id: str | None = None

    control_scope: Literal[
        "local",
        "regional",
        "subnational",
        "national",
        "territorial",
        "unknown",
    ]

    effective_control: bool = False

    control_start_date: date | None = None
    control_end_date: date | None = None

    recognition_status: Literal[
        "un_recognized_government",
        "partially_recognized",
        "contested",
        "not_un_recognized_government",
        "not_applicable",
        "unknown",
    ]

    recognition_source: str | None = None
    recognition_source_url: str | None = None

    source: str
    source_url: str | None = None
    source_version: str | None = None

    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None

    active: bool = True
