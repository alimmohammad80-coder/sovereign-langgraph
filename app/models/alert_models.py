from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Signal(BaseModel):
    title: str
    summary: Optional[str] = ""
    source: Optional[str] = None
    url: Optional[str] = None
    score: Optional[int] = 50
    domain: Optional[str] = None
    created_at: Optional[str] = None


class RecommendedModule(BaseModel):
    module: str
    label: str
    reason: str
    endpoint: str
    priority: int = 1


class OrchestratedAlert(BaseModel):
    alert_id: str
    title: str
    summary: str = ""
    severity: str = "moderate"
    risk_score: int = 50
    velocity: str = "stable"
    confidence: str = "medium"
    domains: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)
    chokepoints: List[str] = Field(default_factory=list)
    signals: List[Signal] = Field(default_factory=list)
    recommended_modules: List[RecommendedModule] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    status: str = "active"
    expires_at: Optional[str] = None
    last_updated: Optional[str] = None
    decay_score: Optional[float] = 0.0

    launch_context: Dict[str, Any] = Field(default_factory=dict)
