from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.data.supply_chain_catalog import SECTORS, CHOKEPOINTS
from app.services.supply_chain_scoring import calculate_supply_chain_risk
from app.services.supply_chain_reasoning import (
    classify_level,
    generate_forecast,
    executive_judgment,
    recommended_actions,
    simulation_questions
)

router = APIRouter(prefix="/api/supply-chain", tags=["Supply Chain Command"])


class SupplyChainRequest(BaseModel):
    country: str
    region: Optional[str] = None
    sector: str
    chokepoint: Optional[str] = None
    commodity: Optional[str] = None
    timeframe: str = "30d"
    limit: int = 5
    signals: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.get("/health")
def health():
    return {
        "status": "online",
        "module": "supply_chain_command_v2",
        "sectors": list(SECTORS.keys()),
        "chokepoints": list(CHOKEPOINTS.keys())
    }


@router.get("/catalog")
def catalog():
    return {
        "status": "success",
        "sectors": SECTORS,
        "chokepoints": CHOKEPOINTS
    }


@router.post("/run-analysis")
def run_analysis(req: SupplyChainRequest):
    result = calculate_supply_chain_risk(
        country=req.country,
        sector=req.sector,
        chokepoint=req.chokepoint,
        commodity=req.commodity,
        custom_signals=req.signals
    )

    score = result["score"]
    level = classify_level(score)
    forecast = generate_forecast(score, result["convergence"])

    return {
        "status": "success",
        "module": "supply_chain_command_v2",
        "country": req.country,
        "region": req.region,
        "sector": req.sector,
        "chokepoint": req.chokepoint,
        "commodity": req.commodity,
        "timeframe": req.timeframe,
        "risk_score": score,
        "risk_level": level,
        "forecast": forecast,
        "convergence_score": result["convergence"],
        "signals_used": result["active_signals"],
        "risk_drivers": result["drivers"],
        "executive_judgment": executive_judgment(
            req.country,
            req.sector,
            req.chokepoint,
            level,
            score,
            result["drivers"]
        ),
        "reasoning": {
            "logic": "Risk is calculated from country exposure, sector criticality, chokepoint vulnerability, commodity specificity, and active disruption signals.",
            "interpretation": f"{level} means the supply chain requires monitoring, mitigation planning, and scenario testing proportional to score severity.",
            "confidence": "Medium-High" if score >= 60 else "Medium"
        },
        "recommended_actions": recommended_actions(level, req.sector),
        "simulation_questions": simulation_questions(req.country, req.sector, req.chokepoint)
    }
