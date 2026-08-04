from __future__ import annotations

from pydantic import BaseModel, Field


class CausalSimulationRequest(BaseModel):
    problem_key: str
    max_depth: int = Field(default=5, ge=1, le=10)
    ignore_lags: bool = True
    persist: bool = False
