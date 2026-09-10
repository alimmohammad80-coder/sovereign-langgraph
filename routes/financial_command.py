from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from routes.financial_corporate_integrated import integrated_status, live_integrated_snapshot
from routes.financial_corporate_reports import FinancialCorporateReportRequest, generate_report
from services.financial_corporate.financial_depth import FinancialDepthService
from services.financial_corporate.risk_engine import CorporateRiskEngine


router = APIRouter(prefix="/api/financial", tags=["Financial Risk Command"])
risk_engine = CorporateRiskEngine()
financial_depth = FinancialDepthService()


DIMENSION_LABELS = {
    "financial_resilience": "Financial Resilience",
    "market_stress": "Market & Credit Stress",
    "supply_chain": "Supply Chain",
    "geopolitical": "Geopolitical",
    "sanctions_compliance": "Sanctions & Compliance",
    "governance_operational": "Governance, Cyber & Operations",
}


class SupplyChainShockRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    dependency_share: float = Field(..., ge=0, le=100)
    disruption_probability: float = Field(..., ge=0, le=100)
    substitutability: float = Field(..., ge=0, le=100)
    recovery_difficulty: float = Field(..., ge=0, le=100)


class CommandReportRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    narrative_refinement: bool = True
    preferred_narrative_provider: Optional[str] = None


def _number(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _normalize_dimensions(overall: Dict[str, Any]) -> List[Dict[str, Any]]:
    scores = overall.get("dimensions") or {}
    confidence = overall.get("dimension_confidence") or {}
    weights = overall.get("weights") or {}
    effective = overall.get("effective_weights") or {}
    contributions = overall.get("weighted_components") or {}

    dimensions: List[Dict[str, Any]] = []
    for key, label in DIMENSION_LABELS.items():
        score = _number(scores.get(key))
        dimensions.append(
            {
                "key": key,
                "label": label,
                "score": score,
                "risk_level": risk_engine.risk_level(score) if score is not None else "Unknown",
                "confidence": _number(confidence.get(key)) or 0.0,
                "weight": _number(weights.get(key)) or 0.0,
                "effective_weight": _number(effective.get(key)) or 0.0,
                "weighted_contribution": _number(contributions.get(key)),
                "status": "observed" if score is not None else "unknown",
            }
        )
    return dimensions


def _normalize_snapshot(live: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    snapshot = live.get("data") or {}
    overall = snapshot.get("overall") or {}
    dimensions = _normalize_dimensions(overall)
    observed = sum(1 for dimension in dimensions if dimension["status"] == "observed")
    total = len(dimensions)
    missing = [dimension["key"] for dimension in dimensions if dimension["status"] == "unknown"]
    coverage_pct = round((observed / total) * 100, 1) if total else 0.0

    return {
        "symbol": symbol,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_status": live.get("status", "unknown"),
        "entity": snapshot.get("entity"),
        "overall": {
            "risk_score": _number(overall.get("overall_risk_score")),
            "risk_level": overall.get("risk_level", "Unknown"),
            "confidence_score": _number(overall.get("confidence_score")) or 0.0,
            "assessment_status": overall.get("assessment_status", "unknown"),
        },
        "coverage": {
            "observed_dimensions": observed,
            "total_dimensions": total,
            "coverage_pct": coverage_pct,
            "missing_dimensions": missing,
        },
        "dimensions": dimensions,
        "top_drivers": overall.get("top_drivers") or [],
        "distress": snapshot.get("distress"),
        "fundamentals": snapshot.get("fundamentals"),
        "market_credit": snapshot.get("market_credit"),
        "external_risk": {
            "supply_chain": (overall.get("dimensions") or {}).get("supply_chain"),
            "geopolitical": (overall.get("dimensions") or {}).get("geopolitical"),
            "sanctions_compliance": (overall.get("dimensions") or {}).get("sanctions_compliance"),
            "governance_operational": (overall.get("dimensions") or {}).get("governance_operational"),
        },
        "evidence": snapshot.get("evidence") or {},
        "collection_errors": live.get("collection_errors") or [],
        "methodology": snapshot.get("methodology"),
        "ai_generated_score": False,
    }


@router.get("/status")
def financial_command_status():
    upstream = integrated_status()
    return {
        "status": "ok",
        "module": "Financial Risk Command",
        "api_version": "v2",
        "canonical": True,
        "authoritative_score": "deterministic",
        "ai_generated_score": False,
        "risk_dimensions": [
            {"key": dimension.key, "label": DIMENSION_LABELS[dimension.key], "weight": dimension.weight}
            for dimension in risk_engine.DIMENSIONS
        ],
        "financial_depth": {
            "status": "enabled",
            "score_policy": "evidence_only_pending_calibration_into_financial_resilience",
            "capabilities": [
                "debt_maturity_and_refinancing",
                "rates_sensitivity",
                "fx_sensitivity_when_disclosed",
                "multi_period_revenue_earnings_cash_flow_debt_trends",
            ],
        },
        "risk_thresholds": {"critical": 85, "high": 70, "elevated": 55, "guarded": 35, "low": 0},
        "upstream": upstream,
    }


@router.get("/snapshot/{symbol}")
def financial_command_snapshot(symbol: str):
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    live = live_integrated_snapshot(normalized_symbol)
    return {
        "status": live.get("status", "success"),
        "data": _normalize_snapshot(live, normalized_symbol),
    }


@router.get("/depth/{symbol}")
def financial_command_depth(symbol: str):
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    try:
        result = financial_depth.collect(normalized_symbol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Financial depth collection failed: {exc}") from exc
    return {
        "status": "success" if result.get("assessment_status") == "complete" else "partial",
        "data": result,
    }


@router.post("/scenario/supply-chain")
def financial_supply_chain_scenario(payload: SupplyChainShockRequest):
    normalized_symbol = payload.symbol.strip().upper()
    live = live_integrated_snapshot(normalized_symbol)
    snapshot = _normalize_snapshot(live, normalized_symbol)
    base_score = snapshot["overall"].get("risk_score")
    if base_score is None:
        raise HTTPException(status_code=422, detail="Insufficient evidence for an authoritative base risk score")

    propagation = risk_engine.propagate_supply_chain_shock(
        base_score=base_score,
        dependency_share=payload.dependency_share,
        disruption_probability=payload.disruption_probability,
        substitutability=payload.substitutability,
        recovery_difficulty=payload.recovery_difficulty,
    )
    return {
        "status": "success",
        "data": {
            "symbol": normalized_symbol,
            "scenario_type": "supply_chain_disruption",
            "base_confidence_score": snapshot["overall"].get("confidence_score"),
            "base_coverage": snapshot["coverage"],
            **propagation,
            "ai_generated_score": False,
        },
    }


@router.post("/reports")
def financial_command_report(payload: CommandReportRequest):
    provider = payload.preferred_narrative_provider
    if provider is not None:
        provider = provider.upper()
        if provider not in {"NVIDIA", "GEMINI", "OPENAI"}:
            raise HTTPException(status_code=422, detail="preferred_narrative_provider must be NVIDIA, GEMINI, or OPENAI")

    return generate_report(
        FinancialCorporateReportRequest(
            symbol=payload.symbol.strip().upper(),
            narrative_refinement=payload.narrative_refinement,
            preferred_narrative_provider=provider,
        )
    )
