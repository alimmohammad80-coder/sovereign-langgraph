from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from .common import (
    ConfidenceGrade,
    ConflictState,
    RegistryRecord,
    ReviewStatus,
)


class HistoricalConflictEpisode(RegistryRecord):
    episode_id: str
    name: str
    short_name: str | None = None

    conflict_category: Literal[
        "interstate",
        "intrastate",
        "internationalized_intrastate",
        "border_conflict",
        "occupation",
        "insurgency",
        "counterinsurgency",
        "proxy_conflict",
        "maritime_conflict",
        "non_state_conflict",
        "other",
    ]

    conflict_subtype: str | None = None

    start_date: date
    end_date: date | None = None

    ongoing: bool = False

    state_participants: list[str] = []
    non_state_organizations: list[str] = []
    governing_authorities: list[str] = []

    territory_refs: list[str] = []
    dispute_refs: list[str] = []
    border_dyad_refs: list[str] = []
    maritime_dyad_refs: list[str] = []
    frozen_conflict_refs: list[str] = []

    initial_trigger: str | None = None
    primary_escalation_driver: str | None = None

    initial_state: ConflictState | None = None
    peak_state: ConflictState | None = None
    terminal_state: ConflictState | None = None

    termination_type: Literal[
        "armistice",
        "ceasefire",
        "peace_agreement",
        "military_victory",
        "regime_collapse",
        "occupation",
        "withdrawal",
        "stalemate",
        "frozen",
        "ongoing",
        "other",
    ] | None = None

    deescalation_method: str | None = None

    battle_deaths_low: int | None = Field(
        default=None,
        ge=0,
    )

    battle_deaths_high: int | None = Field(
        default=None,
        ge=0,
    )

    civilian_deaths: int | None = Field(
        default=None,
        ge=0,
    )

    refugees: int | None = Field(
        default=None,
        ge=0,
    )

    internally_displaced: int | None = Field(
        default=None,
        ge=0,
    )

    economic_damage_estimate: float | None = Field(
        default=None,
        ge=0,
    )

    economic_damage_currency: str | None = None
    economic_damage_year: int | None = None

    air_campaign: bool | None = None
    naval_campaign: bool | None = None
    occupation_occurred: bool | None = None
    foreign_intervention: bool | None = None
    peacekeeping_present: bool | None = None

    territorial_change: bool | None = None
    government_change: bool | None = None
    new_state_created: bool | None = None
    annexation_occurred: bool | None = None
    demilitarized_zone_created: bool | None = None
    sanctions_imposed: bool | None = None
    peace_agreement_signed: bool | None = None

    trigger_summary: str | None = None
    outcome_summary: str | None = None

    strategic_lessons: list[str] = []
    warning_indicators: list[str] = []
    leading_indicators: list[str] = []
    lagging_indicators: list[str] = []

    historical_similarity_vector: dict | None = None

    external_ids: dict[str, str] = {}

    source: str
    source_url: str | None = None
    source_version: str | None = None

    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None

    active: bool = True

    @model_validator(mode="after")
    def validate_dates_and_deaths(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError(
                "end_date cannot precede start_date"
            )

        if not self.ongoing and self.end_date is None:
            raise ValueError(
                "Completed episode requires end_date"
            )

        if (
            self.battle_deaths_low is not None
            and self.battle_deaths_high is not None
            and self.battle_deaths_high
            < self.battle_deaths_low
        ):
            raise ValueError(
                "battle_deaths_high cannot be "
                "lower than battle_deaths_low"
            )

        return self
