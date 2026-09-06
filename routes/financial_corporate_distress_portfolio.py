from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.financial_corporate.distress import CorporateDistressEngine
from services.financial_corporate.portfolio import PortfolioRiskEngine


router = APIRouter(
    prefix="/api/financial-corporate",
    tags=["Financial & Corporate Distress / Portfolio"],
)

distress_engine = CorporateDistressEngine()
portfolio_engine = PortfolioRiskEngine()


class DistressRequest(BaseModel):
    liabilities_to_assets: Optional[float] = None
    current_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    net_margin: Optional[float] = None
    operating_cash_flow_to_debt: Optional[float] = None
    market_stress_score: Optional[float] = Field(None, ge=0, le=100)
    credit_conditions_score: Optional[float] = Field(None, ge=0, le=100)


class PortfolioPosition(BaseModel):
    entity_id: str
    market_value: float = Field(..., gt=0)
    risk_score: Optional[float] = Field(None, ge=0, le=100)
    sector: Optional[str] = None
    country_iso3: Optional[str] = None


class PortfolioRequest(BaseModel):
    positions: List[PortfolioPosition]


class PortfolioStressRequest(BaseModel):
    positions: List[PortfolioPosition]
    shocks: Dict[str, float]
    shock_field: str = "entity_id"


class ContagionEdge(BaseModel):
    source_entity_id: str
    target_entity_id: str
    weight: float = Field(..., ge=0, le=1)
    relationship_type: Optional[str] = None


class ContagionRequest(BaseModel):
    initial_shocks: Dict[str, float]
    edges: List[ContagionEdge]
    rounds: int = Field(3, ge=1, le=10)
    damping: float = Field(0.65, ge=0, le=1)


@router.get("/distress-portfolio/status")
def status():
    return {
        "status": "ok",
        "distress_engine": "corporate_distress_signal_v1",
        "portfolio_engine": "portfolio_risk_v1",
        "contagion_engine": "directed_exposure_contagion_v1",
        "calibrated_probability_of_default": False,
        "ai_generated_scores": False,
    }


@router.post("/distress/score")
def score_distress(payload: DistressRequest):
    result = distress_engine.score(**payload.model_dump())
    return {"status": "success", "data": result, "ai_generated_score": False}


@router.post("/portfolio/analyze")
def analyze_portfolio(payload: PortfolioRequest):
    result = portfolio_engine.analyze([item.model_dump() for item in payload.positions])
    return {"status": "success", "data": result}


@router.post("/portfolio/stress-test")
def stress_test_portfolio(payload: PortfolioStressRequest):
    result = portfolio_engine.stress_test(
        [item.model_dump() for item in payload.positions],
        payload.shocks,
        shock_field=payload.shock_field,
    )
    return {"status": "success", "data": result, "ai_generated_score": False}


@router.post("/portfolio/contagion")
def portfolio_contagion(payload: ContagionRequest):
    result = portfolio_engine.contagion(
        initial_shocks=payload.initial_shocks,
        edges=[edge.model_dump() for edge in payload.edges],
        rounds=payload.rounds,
        damping=payload.damping,
    )
    return {"status": "success", "data": result, "ai_generated_score": False}
