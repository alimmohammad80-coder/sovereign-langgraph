from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from routes.financial_corporate_integrated import integrated_status, live_integrated_snapshot
from routes.financial_corporate_reports import FinancialCorporateReportRequest, generate_report
from services.financial_corporate.financial_depth import FinancialDepthService
from services.financial_corporate.financial_forecast import FinancialRiskForecastEngine
from services.financial_corporate.risk_engine import CorporateRiskEngine
from services.financial_corporate.sector_calibration import SectorRelativeCalibrationEngine

router = APIRouter(prefix="/api/financial", tags=["Financial Risk Command"])
risk_engine = CorporateRiskEngine()
financial_depth = FinancialDepthService()
forecast_engine = FinancialRiskForecastEngine()
sector_calibration = SectorRelativeCalibrationEngine()

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


class SectorCalibrationRequest(BaseModel):
    company_metrics: Dict[str, Any]
    peer_metrics: List[Dict[str, Any]]
    sector_key: Optional[str] = None


def _number(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _freshness(value: Any, *, fresh_days: int, aging_days: int) -> Dict[str, Any]:
    observed = _parse_date(value)
    if observed is None:
        return {"status": "unknown", "observed_at": None, "age_days": None}
    age_days = max(0.0, (datetime.now(timezone.utc) - observed).total_seconds() / 86400.0)
    status = "fresh" if age_days <= fresh_days else "aging" if age_days <= aging_days else "stale"
    return {"status": status, "observed_at": observed.isoformat(), "age_days": round(age_days, 1)}


def _normalize_dimensions(overall: Dict[str, Any]) -> List[Dict[str, Any]]:
    scores = overall.get("dimensions") or {}
    confidence = overall.get("dimension_confidence") or {}
    weights = overall.get("weights") or {}
    effective = overall.get("effective_weights") or {}
    contributions = overall.get("weighted_components") or {}
    dimensions: List[Dict[str, Any]] = []
    for key, label in DIMENSION_LABELS.items():
        score = _number(scores.get(key))
        dimensions.append({
            "key": key,
            "label": label,
            "score": score,
            "risk_level": risk_engine.risk_level(score) if score is not None else "Unknown",
            "confidence": _number(confidence.get(key)) or 0.0,
            "weight": _number(weights.get(key)) or 0.0,
            "effective_weight": _number(effective.get(key)) or 0.0,
            "weighted_contribution": _number(contributions.get(key)),
            "status": "observed" if score is not None else "unknown",
        })
    return dimensions


def _source_freshness(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    evidence = snapshot.get("evidence") or {}
    sec = evidence.get("sec") or {}
    market = snapshot.get("market_credit") or {}
    dynamic = evidence.get("dynamic_hazards") or {}
    diagnostics = evidence.get("cross_module_diagnostics") or {}
    sources = {
        "sec_financials": {
            **_freshness(sec.get("filed") or sec.get("observed_at"), fresh_days=120, aging_days=240),
            "source": sec.get("source") or "SEC EDGAR/XBRL",
            "source_url": sec.get("source_url"),
        },
        "market_credit": {
            **_freshness(market.get("observed_at") or market.get("as_of"), fresh_days=2, aging_days=7),
            "source": "market_and_credit_evidence",
        },
        "cross_module": {
            **_freshness(dynamic.get("observed_at") or diagnostics.get("observed_at"), fresh_days=2, aging_days=7),
            "source": "cross_module_evidence",
        },
    }
    known = [item for item in sources.values() if item["status"] != "unknown"]
    severity = {"fresh": 0, "aging": 1, "stale": 2}
    overall_status = max((item["status"] for item in known), key=lambda status: severity[status], default="unknown")
    return {
        "overall_status": overall_status,
        "known_source_count": len(known),
        "total_source_groups": len(sources),
        "sources": sources,
    }


def _explanation(dimensions: List[Dict[str, Any]], overall: Dict[str, Any]) -> Dict[str, Any]:
    observed = [item for item in dimensions if item.get("score") is not None]
    pressures = sorted(observed, key=lambda item: item.get("weighted_contribution") or 0.0, reverse=True)
    offsets = sorted(observed, key=lambda item: item.get("score") or 0.0)
    largest_pressure = pressures[0] if pressures else None
    strongest_offset = offsets[0] if offsets else None
    score = overall.get("risk_score")
    level = overall.get("risk_level", "Unknown")
    if score is None:
        summary = "There is not enough verified evidence for an authoritative overall assessment."
    elif largest_pressure and strongest_offset:
        summary = (
            f"Overall risk is {level} at {score:.0f}/100. "
            f"{largest_pressure['label']} is the largest measured pressure, while "
            f"{strongest_offset['label']} is currently the strongest offsetting factor."
        )
    else:
        summary = f"Overall risk is {level} at {score:.0f}/100 based on the observed risk dimensions."
    return {
        "summary": summary,
        "largest_pressure": largest_pressure,
        "strongest_offset": strongest_offset,
        "pressures": pressures[:3],
        "offsets": offsets[:3],
        "score_authority": "deterministic",
        "ai_generated": False,
    }


def _normalize_snapshot(live: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    snapshot = live.get("data") or {}
    overall = snapshot.get("overall") or {}
    dimensions = _normalize_dimensions(overall)
    observed = sum(1 for dimension in dimensions if dimension["status"] == "observed")
    total = len(dimensions)
    missing = [dimension["key"] for dimension in dimensions if dimension["status"] == "unknown"]
    normalized_overall = {
        "risk_score": _number(overall.get("overall_risk_score")),
        "risk_level": overall.get("risk_level", "Unknown"),
        "confidence_score": _number(overall.get("confidence_score")) or 0.0,
        "assessment_status": overall.get("assessment_status", "unknown"),
    }
    return {
        "symbol": symbol,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_status": live.get("status", "unknown"),
        "entity": snapshot.get("entity"),
        "overall": normalized_overall,
        "coverage": {
            "observed_dimensions": observed,
            "total_dimensions": total,
            "coverage_pct": round((observed / total) * 100, 1) if total else 0.0,
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
        "freshness": _source_freshness(snapshot),
        "explanation": _explanation(dimensions, normalized_overall),
        "collection_errors": live.get("collection_errors") or [],
        "methodology": snapshot.get("methodology"),
        "ai_generated_score": False,
    }


def _apply_depth_calibration(normalized: Dict[str, Any], live: Dict[str, Any], depth: Dict[str, Any]) -> Dict[str, Any]:
    calibrated = depth.get("calibrated_financial_resilience") or {}
    calibrated_score = _number(calibrated.get("financial_resilience_risk_score"))
    calibrated_confidence = _number(calibrated.get("confidence_score")) or 0.0
    if calibrated_score is None:
        normalized["financial_depth"] = depth
        normalized["score_policy"] = "base_financial_resilience_insufficient_depth_evidence"
        return normalized
    upstream = ((live.get("data") or {}).get("overall") or {})
    factors = dict(upstream.get("dimensions") or {})
    confidence = dict(upstream.get("dimension_confidence") or {})
    base_score = _number(factors.get("financial_resilience"))
    factors["financial_resilience"] = calibrated_score
    confidence["financial_resilience"] = calibrated_confidence
    rescored = risk_engine.score(factors, confidence)
    rescored["dimension_confidence"] = confidence
    normalized["overall"] = {
        "risk_score": _number(rescored.get("overall_risk_score")),
        "risk_level": rescored.get("risk_level", "Unknown"),
        "confidence_score": _number(rescored.get("confidence_score")) or 0.0,
        "assessment_status": rescored.get("assessment_status", "unknown"),
    }
    normalized["dimensions"] = _normalize_dimensions(rescored)
    normalized["top_drivers"] = rescored.get("top_drivers") or []
    normalized["financial_depth"] = depth
    normalized["financial_resilience_calibration"] = {
        "base_score": base_score,
        "calibrated_score": calibrated_score,
        "delta": None if base_score is None else round(calibrated_score - base_score, 2),
        "confidence_score": calibrated_confidence,
        "methodology": calibrated.get("methodology"),
        "guardrails": calibrated.get("guardrails"),
    }
    normalized["explanation"] = _explanation(normalized["dimensions"], normalized["overall"])
    normalized["methodology"] = "financial_risk_command_v2_calibrated_resilience"
    normalized["score_policy"] = "canonical_score_uses_guarded_calibrated_financial_resilience"
    return normalized


@router.get("/status")
def financial_command_status():
    upstream = integrated_status()
    return {
        "status": "ok",
        "module": "Financial Risk Command",
        "api_version": "v2",
        "canonical": True,
        "authoritative_score": "deterministic_guarded_calibration",
        "ai_generated_score": False,
        "risk_dimensions": [
            {"key": dimension.key, "label": DIMENSION_LABELS[dimension.key], "weight": dimension.weight}
            for dimension in risk_engine.DIMENSIONS
        ],
        "financial_depth": {
            "status": "enabled",
            "score_policy": "guarded_calibration_into_financial_resilience",
            "capabilities": [
                "debt_maturity_and_refinancing",
                "company_specific_credit_vulnerability",
                "rates_sensitivity",
                "fx_sensitivity_when_disclosed",
                "multi_period_revenue_earnings_cash_flow_debt_trends",
                "sector_relative_peer_calibration_when_supplied",
                "directional_30_90_180_day_forecasts",
                "deterministic_score_explanation",
                "source_freshness_metadata",
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
    normalized = _normalize_snapshot(live, normalized_symbol)
    try:
        depth = financial_depth.collect(normalized_symbol)
        normalized = _apply_depth_calibration(normalized, live, depth)
    except Exception as exc:
        normalized["financial_depth_error"] = str(exc)
        normalized["score_policy"] = "base_financial_resilience_depth_collection_failed"
    return {"status": live.get("status", "success"), "data": normalized}


@router.get("/depth/{symbol}")
def financial_command_depth(symbol: str):
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    try:
        result = financial_depth.collect(normalized_symbol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Financial depth collection failed: {exc}") from exc
    return {"status": "success" if result.get("assessment_status") == "complete" else "partial", "data": result}


@router.post("/calibrate/sector")
def financial_sector_calibration(payload: SectorCalibrationRequest):
    return {
        "status": "success",
        "data": sector_calibration.calibrate(
            company_metrics=payload.company_metrics,
            peer_metrics=payload.peer_metrics,
            sector_key=payload.sector_key,
        ),
    }


@router.get("/forecast/{symbol}")
def financial_command_forecast(symbol: str):
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    snapshot = financial_command_snapshot(normalized_symbol).get("data") or {}
    depth = snapshot.get("financial_depth") or {}
    external = snapshot.get("external_risk") or {}
    market_credit = snapshot.get("market_credit") or {}
    result = forecast_engine.forecast(
        current_risk_score=(snapshot.get("overall") or {}).get("risk_score"),
        confidence_score=(snapshot.get("overall") or {}).get("confidence_score"),
        market_stress_score=market_credit.get("market_credit_stress_score"),
        refinancing_risk_score=(depth.get("debt_refinancing") or {}).get("refinancing_risk_score"),
        credit_vulnerability_score=(depth.get("credit_vulnerability") or {}).get("credit_vulnerability_score"),
        trend_risk_score=(depth.get("financial_trends") or {}).get("trend_risk_score"),
        supply_chain_risk=external.get("supply_chain"),
        geopolitical_risk=external.get("geopolitical"),
    )
    return {"status": "success", "data": {"symbol": normalized_symbol, **result}}


@router.post("/scenario/supply-chain")
def financial_supply_chain_scenario(payload: SupplyChainShockRequest):
    normalized_symbol = payload.symbol.strip().upper()
    snapshot = financial_command_snapshot(normalized_symbol).get("data") or {}
    base_score = (snapshot.get("overall") or {}).get("risk_score")
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
            "base_confidence_score": (snapshot.get("overall") or {}).get("confidence_score"),
            "base_coverage": snapshot.get("coverage"),
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
