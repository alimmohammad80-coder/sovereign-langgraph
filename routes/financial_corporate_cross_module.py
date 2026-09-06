from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services.financial_corporate.cross_module_edges import CrossModuleExposureBridge
from services.financial_corporate.cross_module_repository import CrossModuleEvidenceRepository
from services.financial_corporate.portfolio import PortfolioRiskEngine


router = APIRouter(
    prefix="/api/financial-corporate/cross-module",
    tags=["Financial & Corporate Cross-Module Intelligence"],
)

bridge = CrossModuleExposureBridge()
repository = CrossModuleEvidenceRepository()
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


class AutomaticContagionRequest(BaseModel):
    initial_shocks: Dict[str, float]
    rounds: int = Field(3, ge=1, le=10)
    damping: float = Field(0.65, ge=0, le=1)
    confidence_floor: float = Field(0, ge=0, le=100)
    limit_per_module: int = Field(1000, ge=1, le=5000)


@router.get("/status")
def status():
    return {
        "status": "ok",
        "module": "Financial & Corporate Cross-Module Intelligence",
        "source_modules": list(bridge.MODULES.values()),
        "edge_schema": "cross_module_exposure_edge_v1",
        "contagion_methodology": "directed_exposure_contagion_v1",
        "automatic_repository_ingestion": True,
        "ai_generated": False,
    }


@router.post("/edges/build")
def build_edges(payload: ModulePayloads):
    result = bridge.build(payload.model_dump())
    return {"status": "success", "data": result}


@router.get("/edges/auto")
def build_automatic_edges(
    limit_per_module: int = Query(1000, ge=1, le=5000),
    confidence_floor: float = Query(0, ge=0, le=100),
):
    collected = repository.collect_all(limit_per_module=limit_per_module)
    built = bridge.build(collected["payloads"])
    eligible = [
        edge for edge in built["edges"]
        if float(edge.get("confidence") or 0.0) >= confidence_floor
    ]
    return {
        "status": "success",
        "data": {
            "edge_count": len(eligible),
            "edges": eligible,
            "source_counts": built["by_module"],
            "confidence_floor": confidence_floor,
            "repository_diagnostics": collected["diagnostics"],
            "ingestion_rule": collected["rule"],
        },
        "ai_generated": False,
    }


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


@router.post("/contagion/auto")
def run_automatic_contagion(payload: AutomaticContagionRequest):
    collected = repository.collect_all(limit_per_module=payload.limit_per_module)
    built = bridge.build(collected["payloads"])
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
            "repository_diagnostics": collected["diagnostics"],
            "ingestion_rule": collected["rule"],
        },
        "ai_generated": False,
    }
