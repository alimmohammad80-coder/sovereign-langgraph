from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .common import ConfidenceGrade, RegistryRecord, ReviewStatus


class Country(RegistryRecord):
    iso3: str = Field(min_length=3, max_length=3)
    iso2: str | None = Field(default=None, min_length=2, max_length=2)
    name: str
    official_name: str | None = None
    region: str | None = None
    subregion: str | None = None
    income_group: str | None = None
    regime_type: str | None = None
    capital: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geometry_ref: str | None = None
    active: bool = True
    source: str
    source_version: str | None = None
    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None


class BorderDyad(RegistryRecord):
    dyad_id: str
    country_a_iso3: str
    country_b_iso3: str
    dyad_type: Literal["land", "maritime", "eez", "mixed"]
    border_length_km: float | None = None
    disputed_flag: bool = False
    dispute_name: str | None = None
    dispute_ref: str | None = None
    militarization_index: float | None = Field(default=None, ge=0, le=100)
    trade_interdependence: float | None = Field(default=None, ge=0, le=1)
    alliance_overlap: float | None = Field(default=None, ge=0, le=1)
    geometry_ref: str | None = None
    active: bool = True
    source: str
    source_version: str | None = None
    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None

    @model_validator(mode="after")
    def validate_order(self):
        if self.country_a_iso3 >= self.country_b_iso3:
            raise ValueError("Dyad members must be stored in canonical alphabetical order.")
        expected = f"DYAD-{self.country_a_iso3}-{self.country_b_iso3}-{self.dyad_type.upper()}"
        if self.dyad_id != expected:
            raise ValueError(f"dyad_id must equal {expected}")
        return self


class Territory(RegistryRecord):
    territory_id: str
    name: str
    de_jure_iso3: str | None = None
    de_facto_controller: str | None = None
    status: Literal[
        "contested", "occupied", "autonomous", "frozen_entity", "disputed", "unresolved"
    ]
    claimants: list[str] = []
    geometry_ref: str | None = None
    active: bool = True
    source: str
    source_version: str | None = None
    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None


class FrozenConflict(RegistryRecord):
    fc_id: str
    name: str
    dispute_id: str | None = None
    parties: list[str]
    territory_id: str | None = None
    primary_dyad_id: str | None = None
    freeze_year: int | None = Field(default=None, ge=1900, le=2100)
    last_flare_date: date | None = None
    mediation_regime: str | None = None
    peacekeeping_presence: bool | None = None
    current_status: str
    reactivation_hazard_score: float | None = Field(default=None, ge=0, le=100)
    hazard_confidence: ConfidenceGrade = ConfidenceGrade.UNKNOWN
    window_watch: bool = False
    source: str
    source_version: str | None = None
    review_status: ReviewStatus
    last_reviewed: date | None = None


class ArmedActor(RegistryRecord):
    actor_id: str
    name: str
    actor_type: Literal[
        "state", "rebel", "militia", "political_armed_group", "jihadist",
        "cartel", "private_military_company", "separatist", "unknown"
    ]
    aliases: list[str] = []
    state_sponsor_iso3: list[str] = []
    estimated_strength: int | None = Field(default=None, ge=0)
    areas_of_operation_ref: str | None = None
    acled_actor_ids: list[str] = []
    ucdp_actor_ids: list[str] = []
    active_from: date | None = None
    active_to: date | None = None
    active: bool = True
    source: str
    source_version: str | None = None
    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None


class ConflictEpisode(RegistryRecord):
    episode_id: str
    external_ids: dict[str, str] = {}
    name: str
    parties: list[str]
    onset_date: date | None = None
    termination_date: date | None = None
    conflict_type: Literal[
        "interstate", "intrastate", "internationalized_intrastate",
        "one_sided", "non_state", "territorial"
    ]
    status: Literal["active", "frozen", "terminated", "latent", "unknown"]
    affected_countries: list[str] = []
    territories: list[str] = []
    peak_state: str | None = None
    source: str
    source_version: str | None = None
    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None


class OntologySummary(BaseModel):
    ontology_version: str
    countries: int
    border_dyads: int
    territories: int
    frozen_conflicts: int
    armed_actors: int
    conflict_episodes: int
    validated_records: int
    provisional_records: int
    last_snapshot_id: str | None = None
    last_updated: str | None = None


class ConflictDispute(RegistryRecord):
    dispute_id: str
    name: str

    dispute_type: Literal[
        "land_boundary",
        "territorial_sovereignty",
        "maritime_boundary",
        "eez",
        "island_sovereignty",
        "occupation",
        "separatist",
        "autonomy",
        "resource",
        "water",
        "demarcation",
        "ceasefire_line",
        "other",
    ]

    status: Literal[
        "latent",
        "active",
        "militarized",
        "negotiating",
        "ceasefire",
        "frozen",
        "resolved",
        "unknown",
    ]

    parties: list[str] = []
    primary_dyad_id: str | None = None
    territory_id: str | None = None
    claimant_iso3: list[str] = []

    maritime: bool = False
    transboundary: bool = False

    start_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )

    last_major_incident: date | None = None

    current_mechanism: str | None = None
    legal_process: str | None = None
    geometry_ref: str | None = None

    source: str
    source_url: str | None = None
    source_version: str | None = None

    confidence_grade: ConfidenceGrade
    review_status: ReviewStatus
    last_reviewed: date | None = None

    active: bool = True
