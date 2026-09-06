from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.financial_corporate.market_credit import MarketCreditIntelligenceService
from services.financial_corporate.orchestrator import FinancialCorporateOrchestrator
from services.financial_corporate.sec_edgar import SECConfigurationError, SECEdgarCollector


router = APIRouter(
    prefix="/api/financial-corporate/integrated",
    tags=["Financial & Corporate Integrated Intelligence"],
)

orchestrator = FinancialCorporateOrchestrator()
market_credit = MarketCreditIntelligenceService()
sec = SECEdgarCollector()


class IntegratedSnapshotRequest(BaseModel):
    entity_reference: Optional[str] = None
    financial_observations: Optional[Dict[str, Any]] = None
    market_analysis: Optional[Dict[str, Any]] = None
    credit_analysis: Optional[Dict[str, Any]] = None
    supply_chain_risk: Optional[float] = Field(None, ge=0, le=100)
    geopolitical_risk: Optional[float] = Field(None, ge=0, le=100)
    sanctions_risk: Optional[float] = Field(None, ge=0, le=100)
    governance_operational_risk: Optional[float] = Field(None, ge=0, le=100)
    evidence: Optional[Dict[str, Any]] = None


@router.get("/status")
def integrated_status():
    provider_status = market_credit.provider_status()
    return {
        "status": "ok",
        "module": "Financial & Corporate Risk Intelligence",
        "orchestrator": "financial_corporate_integrated_snapshot_v1",
        "providers": {
            "sec_edgar": {"configured": sec.configured, "required_env": "SEC_USER_AGENT"},
            **provider_status,
        },
        "optional_env": [
            "ALPHA_VANTAGE_API_KEY",
            "FINCORP_SUPPLY_CHAIN_EXPOSURE_TABLE",
            "FINCORP_COUNTRY_EXPOSURE_TABLE",
            "FINCORP_CONFLICT_EXPOSURE_TABLE",
            "FINCORP_SANCTIONS_EXPOSURE_TABLE",
            "FINCORP_CYBER_EXPOSURE_TABLE",
        ],
        "scoring": {
            "ai_generated": False,
            "corporate_risk": "deterministic_weighted_multifactor_v1",
            "distress": "corporate_distress_signal_v1",
            "market_credit": "confidence_weighted_market_credit_v1",
        },
    }


@router.post("/snapshot")
def integrated_snapshot(payload: IntegratedSnapshotRequest):
    return {
        "status": "success",
        "data": orchestrator.build_snapshot(**payload.model_dump()),
    }


@router.get("/live/{symbol}")
def live_integrated_snapshot(symbol: str):
    symbol = symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")

    errors = []
    financial_observations = None
    entity_reference = symbol
    sec_evidence = None

    try:
        resolved = sec.resolve_ticker(symbol)
        if resolved:
            entity_reference = resolved.get("ticker") or symbol
            facts = sec.fetch_company_facts(resolved["cik"])
            financial_observations = facts.get("financial_observations")
            sec_evidence = {
                "cik": resolved.get("cik"),
                "title": resolved.get("title"),
                "source": "SEC EDGAR/XBRL",
                "source_url": facts.get("source_url"),
            }
        else:
            errors.append({"component": "sec_edgar", "error": f"Ticker {symbol} not found in SEC index"})
    except SECConfigurationError as exc:
        errors.append({"component": "sec_edgar", "error": str(exc)})
    except Exception as exc:
        errors.append({"component": "sec_edgar", "error": str(exc)})

    market_analysis = None
    try:
        market_analysis = market_credit.company_market_snapshot(symbol).get("analysis")
    except Exception as exc:
        errors.append({"component": "equity_market", "error": str(exc)})

    credit_analysis = None
    try:
        credit_analysis = market_credit.credit_snapshot().get("analysis")
    except Exception as exc:
        errors.append({"component": "credit_conditions", "error": str(exc)})

    snapshot = orchestrator.build_snapshot(
        entity_reference=entity_reference,
        financial_observations=financial_observations,
        market_analysis=market_analysis,
        credit_analysis=credit_analysis,
        evidence={"sec": sec_evidence, "collection_errors": errors},
    )

    return {
        "status": "success" if not errors else "partial",
        "symbol": symbol,
        "data": snapshot,
        "collection_errors": errors,
        "ai_generated_score": False,
    }
