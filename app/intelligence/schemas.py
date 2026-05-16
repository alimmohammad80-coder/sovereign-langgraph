from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class IntelligenceIndicatorRequest(BaseModel):
    module: str = Field(..., description="Module name, e.g. strategic_early_warning")
    entity: str = Field(..., description="Country, company, route, sector, or issue")
    indicator: str = Field(..., description="Specific indicator to run")
    limit: int = 10


class IntelligenceSignal(BaseModel):
    title: str
    summary: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    domain: Optional[str] = None
    severity: int = 50
    confidence: str = "Moderate"


class IntelligenceRunResult(BaseModel):
    status: str = "success"
    entity: str
    module: str
    indicator: str
    score: int
    level: str
    signals: List[IntelligenceSignal]
    executive_judgment: str
    strategic_assessment: str
    cross_domain_impacts: Dict[str, Any]
    confidence: str
    intelligence_gaps: List[str]
    recommended_actions: List[str]
    simulation_ready: bool
    simulation_triggers: List[str]
    related_entities: List[str]
