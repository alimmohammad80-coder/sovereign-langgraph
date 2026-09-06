from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.financial_corporate import CorporateEntityMaster, CorporateRiskEngine


router = APIRouter(
    prefix="/api/financial-corporate",
    tags=["Financial & Corporate Risk Intelligence"],
)

entity_master = CorporateEntityMaster()
risk_engine = CorporateRiskEngine()


class CorporateRiskScoreRequest(BaseModel):
    entity_id: Optional[str] = None
    entity_reference: Optional[str] = None
    financial_resilience: float = Field(..., ge=0, le=100)
    market_stress: float = Field(..., ge=0, le=100)
    supply_chain: float = Field(..., ge=0, le=100)
    geopolitical: float = Field(..., ge=0, le=100)
    sanctions_compliance: float = Field(..., ge=0, le=100)
    governance_operational: float = Field(..., ge=0, le=100)
    evidence_coverage: Optional[Dict[str, float]] = None


class SupplyChainPropagationRequest(BaseModel):
    entity_id: Optional[str] = None
    entity_reference: Optional[str] = None
    base_risk_score: float = Field(..., ge=0, le=100)
    dependency_share: float = Field(..., ge=0, le=100)
    disruption_probability: float = Field(..., ge=0, le=100)
    substitutability: float = Field(..., ge=0, le=100)
    recovery_difficulty: float = Field(..., ge=0, le=100)


def _resolve_entity(entity_id: Optional[str], entity_reference: Optional[str]):
    if entity_id:
        entity = entity_master.get_entity(entity_id)
        if entity:
            return entity
    if entity_reference:
        entity = entity_master.resolve(entity_reference)
        if entity:
            return entity
    if entity_id or entity_reference:
        raise HTTPException(status_code=404, detail="Corporate entity not found")
    return None


@router.get("/health")
def health():
    return {
        "status": "ok",
        "module": "Financial & Corporate Risk Intelligence",
        "scoring_mode": "deterministic",
        "entity_master": "corporate_entity_master_v1",
        "risk_engine": "deterministic_weighted_multifactor_v1",
    }


@router.get("/architecture")
def architecture():
    return {
        "module": "Financial & Corporate Risk Intelligence",
        "principles": [
            "Preserve existing Financial Risk Command endpoints during migration",
            "Use one canonical company identity across financial and supply-chain intelligence",
            "Calculate risk with deterministic/statistical models rather than LLM-generated probabilities",
            "Use AI models for explanation, synthesis, citation-aware reporting and scenario narration",
        ],
        "layers": [
            "Corporate Entity Master",
            "Provider and Evidence Layer",
            "Deterministic Corporate Risk Engine",
            "Supply-Chain-to-Financial Transmission Layer",
            "Portfolio and Contagion Layer",
            "AI Explanation and Reporting Layer",
        ],
        "next_providers": ["SEC EDGAR/XBRL", "GLEIF", "OFAC", "macro/market feeds"],
    }


@router.get("/companies")
def list_companies(
    query: Optional[str] = None,
    country_iso3: Optional[str] = Query(None, min_length=3, max_length=3),
    sector: Optional[str] = None,
    tier: Optional[int] = Query(None, ge=1, le=3),
    limit: int = Query(50, ge=1, le=250),
):
    companies = entity_master.list_entities(
        query=query,
        country_iso3=country_iso3,
        sector=sector,
        tier=tier,
        limit=limit,
    )
    return {"status": "success", "count": len(companies), "data": companies}


@router.get("/companies/{entity_id}")
def get_company(entity_id: str):
    company = entity_master.get_entity(entity_id)
    if not company:
        raise HTTPException(status_code=404, detail="Corporate entity not found")
    return {"status": "success", "data": company}


@router.get("/resolve")
def resolve_company(reference: str = Query(..., min_length=1)):
    company = entity_master.resolve(reference)
    if not company:
        raise HTTPException(status_code=404, detail="Corporate entity not found")
    return {"status": "success", "reference": reference, "data": company}


@router.post("/risk/score")
def score_corporate_risk(payload: CorporateRiskScoreRequest):
    entity = _resolve_entity(payload.entity_id, payload.entity_reference)
    factors = {
        "financial_resilience": payload.financial_resilience,
        "market_stress": payload.market_stress,
        "supply_chain": payload.supply_chain,
        "geopolitical": payload.geopolitical,
        "sanctions_compliance": payload.sanctions_compliance,
        "governance_operational": payload.governance_operational,
    }
    result = risk_engine.score(factors, payload.evidence_coverage)
    return {
        "status": "success",
        "entity": entity,
        "result": result,
        "ai_generated_score": False,
    }


@router.post("/exposure/supply-chain-propagation")
def propagate_supply_chain_risk(payload: SupplyChainPropagationRequest):
    entity = _resolve_entity(payload.entity_id, payload.entity_reference)
    result = risk_engine.propagate_supply_chain_shock(
        base_score=payload.base_risk_score,
        dependency_share=payload.dependency_share,
        disruption_probability=payload.disruption_probability,
        substitutability=payload.substitutability,
        recovery_difficulty=payload.recovery_difficulty,
    )
    return {
        "status": "success",
        "entity": entity,
        "source_module": "Supply Chain Intelligence",
        "target_module": "Financial & Corporate Risk Intelligence",
        "result": result,
        "ai_generated_score": False,
    }
