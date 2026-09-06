from __future__ import annotations

from typing import Dict, Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.financial_corporate import (
    CorporateEntityMaster,
    CorporateFundamentalsAnalyzer,
    CorporateRiskEngine,
    GLEIFCollector,
    SECEdgarCollector,
    SECConfigurationError,
)
from services.financial_corporate.providers import FinancialCorporateProviderRegistry


router = APIRouter(
    prefix="/api/financial-corporate",
    tags=["Financial & Corporate Risk Intelligence"],
)

entity_master = CorporateEntityMaster()
risk_engine = CorporateRiskEngine()
provider_registry = FinancialCorporateProviderRegistry()
sec_collector = SECEdgarCollector()
gleif_collector = GLEIFCollector()
fundamentals_analyzer = CorporateFundamentalsAnalyzer()


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


def _provider_error(provider: str, exc: Exception) -> HTTPException:
    if isinstance(exc, SECConfigurationError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 502
        return HTTPException(status_code=502, detail=f"{provider} upstream HTTP {status}")
    if isinstance(exc, requests.RequestException):
        return HTTPException(status_code=502, detail=f"{provider} upstream request failed")
    return HTTPException(status_code=500, detail=f"{provider} collector failed: {exc}")


@router.get("/health")
def health():
    return {
        "status": "ok",
        "module": "Financial & Corporate Risk Intelligence",
        "scoring_mode": "deterministic",
        "entity_master": "corporate_entity_master_v1",
        "risk_engine": "deterministic_weighted_multifactor_v1",
        "sec_edgar_configured": sec_collector.configured,
        "gleif_configured": True,
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
        "providers": provider_registry.capabilities(),
        "provider_contract": provider_registry.architecture(),
    }


@router.get("/providers")
def providers():
    capabilities = provider_registry.capabilities()
    return {
        "status": "success",
        "count": len(capabilities),
        "data": capabilities,
        "contract": provider_registry.architecture(),
    }


@router.get("/providers/sec/status")
def sec_status():
    return {
        "status": "ok" if sec_collector.configured else "configuration_required",
        "provider": "sec_edgar",
        "configured": sec_collector.configured,
        "required_environment": ["SEC_USER_AGENT"],
        "auth_required": False,
    }


@router.get("/providers/sec/ticker/{ticker}")
def sec_resolve_ticker(ticker: str):
    try:
        record = sec_collector.resolve_ticker(ticker)
    except Exception as exc:
        raise _provider_error("SEC EDGAR", exc)
    if not record:
        raise HTTPException(status_code=404, detail="Ticker not found in SEC company index")
    return {"status": "success", "data": record}


@router.get("/providers/sec/company/{cik}")
def sec_company_snapshot(cik: str):
    try:
        data = sec_collector.company_snapshot(cik)
    except Exception as exc:
        raise _provider_error("SEC EDGAR", exc)
    return {"status": "success", "data": data}


@router.get("/providers/sec/company/{cik}/fundamentals")
def sec_company_fundamentals(cik: str):
    try:
        facts = sec_collector.fetch_company_facts(cik)
        analysis = fundamentals_analyzer.analyze(facts.get("financial_observations") or {})
    except Exception as exc:
        raise _provider_error("SEC EDGAR", exc)
    return {
        "status": "success",
        "identity": facts.get("identity"),
        "observations": facts.get("financial_observations"),
        "analysis": analysis,
        "source_url": facts.get("source_url"),
        "ai_generated_score": False,
    }


@router.get("/providers/gleif/search")
def gleif_search(
    name: str = Query(..., min_length=2),
    country: Optional[str] = Query(None, min_length=2, max_length=2),
    limit: int = Query(10, ge=1, le=100),
):
    try:
        data = gleif_collector.search_by_name(name, country=country, limit=limit)
    except Exception as exc:
        raise _provider_error("GLEIF", exc)
    return {"status": "success", "count": len(data), "data": data}


@router.get("/providers/gleif/{lei}")
def gleif_record(lei: str):
    try:
        data = gleif_collector.get_lei(lei)
    except Exception as exc:
        raise _provider_error("GLEIF", exc)
    return {"status": "success", "data": data}


@router.get("/providers/gleif/{lei}/relationships")
def gleif_relationships(lei: str):
    try:
        data = gleif_collector.relationships(lei)
    except Exception as exc:
        raise _provider_error("GLEIF", exc)
    return {"status": "success", "data": data}


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


@router.get("/companies/{entity_id}/live-evidence")
def company_live_evidence(entity_id: str):
    company = entity_master.get_entity(entity_id)
    if not company:
        raise HTTPException(status_code=404, detail="Corporate entity not found")

    result = {
        "entity": company,
        "sec_edgar": None,
        "gleif": None,
        "warnings": [],
    }

    tickers = company.get("tickers") or []
    if tickers and sec_collector.configured:
        try:
            sec_identity = None
            for ticker in tickers:
                sec_identity = sec_collector.resolve_ticker(str(ticker))
                if sec_identity:
                    break
            if sec_identity:
                snapshot = sec_collector.company_snapshot(sec_identity["cik"])
                analysis = fundamentals_analyzer.analyze(snapshot.get("financial_observations") or {})
                result["sec_edgar"] = {
                    "resolved": sec_identity,
                    "snapshot": snapshot,
                    "fundamental_analysis": analysis,
                }
        except Exception as exc:
            result["warnings"].append(f"SEC EDGAR: {exc}")
    elif not sec_collector.configured:
        result["warnings"].append("SEC EDGAR disabled until SEC_USER_AGENT is configured")

    try:
        country2 = None
        gleif_match = gleif_collector.best_match(str(company.get("legal_name") or ""), country=country2)
        if gleif_match:
            result["gleif"] = gleif_match
    except Exception as exc:
        result["warnings"].append(f"GLEIF: {exc}")

    return {
        "status": "success",
        "data": result,
        "provider_scores_are_final_risk_scores": False,
    }


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
