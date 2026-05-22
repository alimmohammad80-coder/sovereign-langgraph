from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    source_module: Optional[str] = Field(default="manual")
    scenario_type: Optional[str] = Field(default="adaptive")
    country: Optional[str] = None
    region: Optional[str] = None
    sector: Optional[str] = None
    entity: Optional[str] = None
    event: str
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    time_horizon: Optional[str] = Field(default="30 days")
    drivers: List[str] = Field(default_factory=list)
    indicators: List[str] = Field(default_factory=list)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    live_sources: Dict[str, Any] = Field(default_factory=dict)
    source_report: Dict[str, Any] = Field(default_factory=dict)
    user_question: Optional[str] = None


class FollowUpScenarioRequest(BaseModel):
    original_context: Dict[str, Any]
    selected_question: str
    time_horizon: Optional[str] = "30 days"
