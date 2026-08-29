from __future__ import annotations

from pydantic import BaseModel, Field


class ConflictAgentAnalysisRequest(BaseModel):

    countries: list[str] = Field(
        min_length=1,
        max_length=10,
    )

    region: str | None = None

    conflict_type: str | None = None

    indicators: list[str] = Field(
        default_factory=list
    )

    horizon_days: int = Field(
        default=365,
        ge=30,
        le=365,
    )

    lookback_days: int = Field(
        default=90,
        ge=1,
        le=365,
    )

    ripple_depth: int = Field(
        default=3,
        ge=1,
        le=4,
    )
