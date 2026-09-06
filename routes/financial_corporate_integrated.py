from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.financial_corporate.advanced_hazards import AdvancedCorporateHazardService
from services.financial_corporate.cross_module_edges import CrossModuleExposureBridge
from services.financial_corporate.cross_module_repository import CrossModuleEvidenceRepository
from services.financial_corporate.cross_module_scoring import CrossModuleRiskScorer
from services.financial_corporate.market_credit import MarketCreditIntelligenceService
from services.financial_corporate.orchestrator import FinancialCorporateOrchestrator
from services.financial_corporate.sec_edgar import SECConfigurationError, SECEdgarCollector
from services.financial_corporate.self_test import FinancialCorporateSelfTest


router = APIRouter(
    prefix="/api/financial-corporate/integrated",
    tags=["Financial & Corporate Integrated Intelligence"],
)

orchestrator = FinancialCorporateOrchestrator()
market_credit = MarketCreditIntelligenceService()
sec = SECEdgarCollector()
self_test_runner = FinancialCorporateSelfTest()
cross_module_repository = CrossModuleEvidenceRepository()
cross_module_bridge = CrossModuleExposureBridge()
cross_module_hazards = AdvancedCorporateHazardService()
cross_module_scorer = CrossModuleRiskScorer()


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
        "orchestrator": "financial_corporate_integrated_snapshot_v3_dynamic_hazards",
        "providers": {
            "sec_edgar": {"configured": sec.configured, "required_env": "SEC_USER_AGENT"},
            **provider_status,
            "country_intelligence": {"role": "stored deterministic country hazard by ISO3 with freshness decay"},
            "conflict_forecasting": {"role": "dynamic conflict/security hazard"},
            "ofac_sls": {"role": "direct sanctions designation screening"},
            "trade_control_signals": {"role": "company-specific export-control and trade-restriction pressure"},
            "cisa_kev": {"role": "company-vendor known exploited vulnerability pressure"},
            "nvd": {"role": "recent company/product vulnerability pressure"},
            "cyber_media_signals": {"role": "company-specific cyber operational pressure"},
        },
        "optional_env": [
            "ALPHA_VANTAGE_API_KEY",
            "NVD_API_KEY",
            "FINCORP_SUPPLY_CHAIN_EXPOSURE_TABLE",
            "FINCORP_COUNTRY_EXPOSURE_TABLE",
            "FINCORP_CONFLICT_EXPOSURE_TABLE",
            "FINCORP_SANCTIONS_EXPOSURE_TABLE",
            "FINCORP_CYBER_EXPOSURE_TABLE",
        ],
        "scoring": {
            "ai_generated": False,
            "corporate_risk": "deterministic_weighted_multifactor_v2_missing_aware",
            "distress": "corporate_distress_signal_v1",
            "market_credit": "confidence_weighted_market_credit_v1",
            "cross_module": "cross_module_exposure_hazard_confidence_v2",
            "dynamic_hazards": "cross_module_dynamic_hazard_enrichment_v2_production_hardened",
        },
        "cross_module_formula": "risk_contribution = structural_exposure * dynamic_hazard * evidence_confidence",
        "evidence_rules": [
            "Country evidence confidence decays with age.",
            "Negative sanctions/cyber screening does not imply zero risk.",
            "Dynamic graph payloads are scoped to the requested company.",
        ],
    }


@router.get("/self-test")
def integrated_self_test():
    result = self_test_runner.run()
    return {
        "status": "success" if result["status"] == "pass" else "degraded",
        "data": result,
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

    cross_module = None
    cross_module_diagnostics = None
    dynamic_hazards = None
    supply_chain_risk = None
    geopolitical_risk = None
    sanctions_risk = None
    governance_operational_risk = None

    try:
        entity = orchestrator.entity_master.resolve(entity_reference)
        company_entity_id = (entity or {}).get("entity_id") if isinstance(entity, dict) else None
        if company_entity_id and isinstance(entity, dict):
            collected = cross_module_repository.collect_all(limit_per_module=1000)
            built = cross_module_bridge.build(collected.get("payloads") or {})
            dynamic_hazards = cross_module_hazards.enrich(
                company_entity_id=company_entity_id,
                entity=entity,
                edges=built.get("edges") or [],
            )
            cross_module = cross_module_scorer.score_company(
                company_entity_id,
                dynamic_hazards.get("edges") or [],
            )
            cross_module_diagnostics = collected.get("diagnostics")
            scores = cross_module.get("scores") or {}
            supply_chain_risk = scores.get("supply_chain")
            geopolitical_risk = scores.get("geopolitical")
            sanctions_risk = scores.get("sanctions_compliance")
            governance_operational_risk = scores.get("governance_operational")
    except Exception as exc:
        errors.append({"component": "cross_module_evidence", "error": str(exc)})

    evidence = {
        "sec": sec_evidence,
        "cross_module": cross_module,
        "cross_module_diagnostics": cross_module_diagnostics,
        "dynamic_hazards": dynamic_hazards,
        "collection_errors": errors,
    }

    snapshot = orchestrator.build_snapshot(
        entity_reference=entity_reference,
        financial_observations=financial_observations,
        market_analysis=market_analysis,
        credit_analysis=credit_analysis,
        supply_chain_risk=supply_chain_risk,
        geopolitical_risk=geopolitical_risk,
        sanctions_risk=sanctions_risk,
        governance_operational_risk=governance_operational_risk,
        evidence=evidence,
    )

    return {
        "status": "success" if not errors else "partial",
        "symbol": symbol,
        "data": snapshot,
        "collection_errors": errors,
        "ai_generated_score": False,
    }
