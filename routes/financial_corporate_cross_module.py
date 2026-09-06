from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.financial_corporate.cross_module_edges import CrossModuleExposureBridge
from services.financial_corporate.portfolio import PortfolioRiskEngine


router = APIRouter(
    prefix="/api/financial-corporate/cross-module",
    tags=["Financial & Corporate Cross-Module Intelligence"],
)

bridge = CrossModuleExposureBridge()
portfolio_engine = PortfolioRiskEngine()


class ModulePayloads(BaseModel):
    supply_chain: List[Dict[str, Any]] = Field(default_factory=list)
    country: List[Dict[str, Any]] = Field(default_factory=list)
    conflict: List[Dict[str, Any]] = Field(default_factory=list)
    sanctions: List[Dict[str, Any]] = Field(default_factory=list)
    cyber: List[Dict[str, Any]] = Field(default_factory=list)


class CrossModuleContagionRequest(ModulePayloads):
    initial_shocks: Dict[str, float]
    rounds: int = Field(3, ge=1, le=10)
    damping: float = Field(0.65, ge=0, le=1)
    confidence_floor: float = Field(0, ge=0, le=100)


@router.get("/status")
def status():
    return {
        "status": "ok",
        "module": "Financial & Corporate Cross-Module Intelligence",
        "source_modules": list(bridge.MODULES.values()),
        "edge_schema": "cross_module_exposure_edge_v1",
        "contagion_methodology": "directed_exposure_contagion_v1",
        "ai_generated": False,
    }


@router.post("/edges/build")
def build_edges(payload: ModulePayloads):
    result = bridge.build(payload.model_dump())
    return {"status": "success", "data": result}


@router.post("/contagion/run")
def run_cross_module_contagion(payload: CrossModuleContagionRequest):
    built = bridge.build(payload.model_dump())
    eligible_edges = [
        edge for edge in built["edges"]
        if float(edge.get("confidence") or 0.0) >= payload.confidence_floor
    ]
    contagion = portfolio_engine.contagion(
        initial_shocks=payload.initial_shocks,
        edges=eligible_edges,
        rounds=payload.rounds,
        damping=payload.damping,
    )
    return {
        "status": "success",
        "data": {
            "edge_graph": {
                "edge_count": len(eligible_edges),
                "source_counts": built["by_module"],
                "confidence_floor": payload.confidence_floor,
                "edges": eligible_edges,
            },
            "contagion": contagion,
        },
        "ai_generated": False,
    }
