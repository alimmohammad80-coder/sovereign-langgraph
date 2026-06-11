from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client, Client
from routers.country_signal_sources import fetch_country_signals, analyze_signal_convergence
from routers.country_nemotron_reasoning import run_nemotron_country_reasoning

router = APIRouter(prefix="/api/country-intelligence", tags=["Country Intelligence"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


class CountryScoreInput(BaseModel):
    political_stability: int = Field(50, ge=0, le=100)
    military_activity: int = Field(50, ge=0, le=100)
    economic_stress: int = Field(50, ge=0, le=100)
    energy_security: int = Field(50, ge=0, le=100)
    supply_chain_exposure: int = Field(50, ge=0, le=100)
    cyber_threat: int = Field(50, ge=0, le=100)
    social_stability: int = Field(50, ge=0, le=100)
    diplomatic_tensions: int = Field(50, ge=0, le=100)
    regulatory_risk: int = Field(50, ge=0, le=100)
    strategic_outlook: int = Field(50, ge=0, le=100)
    analyst_notes: Optional[str] = None
    updated_by: Optional[str] = None


class CountryRunInput(BaseModel):
    iso3: str
    country_name: Optional[str] = None
    timeframe: str = "30 days"


def require_supabase():
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Supabase is not configured. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )



def build_frontend_summary(signals, convergence):
    critical_count = sum(1 for s in signals if s.get("severity") == "critical")
    high_count = sum(1 for s in signals if s.get("severity") == "high")

    clean_signals = []
    for s in signals:
        clean_signals.append({
            "title": s.get("title"),
            "source": s.get("source"),
            "published_at": s.get("published_at"),
            "signal_domain": s.get("signal_domain"),
            "severity": s.get("severity"),
            "summary": s.get("summary"),
            "source_url": s.get("url")
        })

    confidence = "High" if len(signals) >= 6 else "Medium" if len(signals) >= 3 else "Low"

    return {
        "source_count": len(signals),
        "critical_signal_count": critical_count,
        "high_signal_count": high_count,
        "confidence": confidence,
        "clean_signals": clean_signals,
        "convergence_level": convergence.get("convergence_level"),
        "dominant_domains": convergence.get("dominant_domains", [])
    }


def calculate_country_score(scores: Dict[str, Any]):
    weights = {
        "political_stability": 0.15,
        "military_activity": 0.15,
        "economic_stress": 0.15,
        "energy_security": 0.10,
        "supply_chain_exposure": 0.15,
        "cyber_threat": 0.05,
        "social_stability": 0.10,
        "diplomatic_tensions": 0.10,
        "regulatory_risk": 0.03,
        "strategic_outlook": 0.02,
    }

    score = round(sum(int(scores.get(k, 50)) * w for k, w in weights.items()))

    if score >= 81:
        level = "Critical"
    elif score >= 61:
        level = "High"
    elif score >= 41:
        level = "Elevated"
    elif score >= 21:
        level = "Guarded"
    else:
        level = "Low"

    return score, level


@router.get("/health")
def health():
    return {
        "status": "ok",
        "module": "country_intelligence",
        "supabase_configured": bool(supabase),
        "timestamp": datetime.utcnow().isoformat()
    }



@router.get("/debug/signals/{country_name}")
def debug_country_signals(country_name: str, limit: int = 8):
    signals = fetch_country_signals(country_name, limit=limit)
    return {
        "status": "success",
        "country_name": country_name,
        "count": len(signals),
        "data": signals
    }


@router.get("/countries")
def list_countries():
    require_supabase()

    res = (
        supabase.table("country_registry")
        .select("*")
        .order("is_priority", desc=True)
        .order("country_name")
        .execute()
    )

    return {
        "status": "success",
        "count": len(res.data or []),
        "data": res.data or []
    }


@router.get("/{iso3}/scores")
def get_country_scores(iso3: str):
    require_supabase()

    iso3 = iso3.upper()

    res = (
        supabase.table("country_risk_scores")
        .select("*")
        .eq("iso3", iso3)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    if not res.data:
        return {
            "status": "empty",
            "iso3": iso3,
            "message": "No analyst scores found for this country yet."
        }

    return {
        "status": "success",
        "data": res.data[0]
    }


@router.post("/{iso3}/scores")
def upsert_country_scores(iso3: str, payload: CountryScoreInput):
    require_supabase()

    iso3 = iso3.upper()

    country_lookup = (
        supabase.table("country_registry")
        .select("country_name")
        .eq("iso3", iso3)
        .limit(1)
        .execute()
    )
    country_name = country_lookup.data[0]["country_name"] if country_lookup.data else iso3

    scores = payload.model_dump()
    overall_score, risk_level = calculate_country_score(scores)

    row = {
        **scores,
        "iso3": iso3,
        "country_code": iso3,
        "country_name": country_name,
        "overall_score": overall_score,
        "risk_level": risk_level,
        "updated_at": datetime.utcnow().isoformat()
    }

    existing = (
        supabase.table("country_risk_scores")
        .select("id")
        .eq("iso3", iso3)
        .limit(1)
        .execute()
    )

    if existing.data:
        res = (
            supabase.table("country_risk_scores")
            .update(row)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        res = (
            supabase.table("country_risk_scores")
            .insert(row)
            .execute()
        )

    return {
        "status": "success",
        "iso3": iso3,
        "country_code": iso3,
        "overall_score": overall_score,
        "risk_level": risk_level,
        "data": res.data[0] if res.data else row
    }



@router.post("/run")
def run_country_intelligence(payload: CountryRunInput):
    require_supabase()

    iso3 = payload.iso3.upper()

    country_res = (
        supabase.table("country_registry")
        .select("*")
        .eq("iso3", iso3)
        .limit(1)
        .execute()
    )

    if not country_res.data:
        raise HTTPException(status_code=404, detail=f"Country {iso3} not found in country_registry.")

    country = country_res.data[0]
    country_name = payload.country_name or country.get("country_name") or iso3

    score_res = (
        supabase.table("country_risk_scores")
        .select("*")
        .eq("iso3", iso3)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    scores = score_res.data[0] if score_res.data else {
        "overall_score": 50,
        "risk_level": "Guarded",
        "political_stability": 50,
        "military_activity": 50,
        "economic_stress": 50,
        "energy_security": 50,
        "supply_chain_exposure": 50,
        "cyber_threat": 50,
        "social_stability": 50,
        "diplomatic_tensions": 50,
        "regulatory_risk": 50,
        "strategic_outlook": 50,
        "analyst_notes": "Default baseline score used because no analyst score exists yet."
    }

    risk_score = scores.get("overall_score", 50)
    risk_level = scores.get("risk_level", "Guarded")

    live_signals = fetch_country_signals(country_name, limit=8)
    signal_convergence = analyze_signal_convergence(live_signals)

    saved_signals = []
    for signal in live_signals:
        signal_row = {
            "iso3": iso3,
            "title": signal.get("title"),
            "source": signal.get("source"),
            "url": signal.get("url"),
            "published_at": None,
            "signal_domain": signal.get("signal_domain"),
            "severity": signal.get("severity"),
            "summary": signal.get("summary")
        }

        try:
            inserted = supabase.table("country_signals").insert(signal_row).execute()
            if inserted.data:
                saved_signals.append(inserted.data[0])
        except Exception as e:
            # Do not fail report generation because signal storage failed.
            signal_row["storage_error"] = str(e)
            saved_signals.append(signal_row)

    frontend_summary = build_frontend_summary(live_signals, signal_convergence)

    ai_reasoning = run_nemotron_country_reasoning(
        country_name=country_name,
        risk_score=risk_score,
        risk_level=risk_level,
        scores=scores,
        signals=live_signals,
        convergence=signal_convergence,
        timeframe=payload.timeframe
    )

    report = {
        "iso3": iso3,
        "country_name": country_name,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "executive_judgment": ai_reasoning.get("executive_judgment") or f"{country_name} is assessed at {risk_level} risk with a score of {risk_score}/100.",
        "strategic_signals": live_signals,
        "signal_convergence": signal_convergence,
        "frontend_summary": frontend_summary,
        "risk_context": ai_reasoning.get("risk_context") or f"{country_name}'s country risk context is based on analyst scoring, strategic geography, and {len(live_signals)} current open-source signals.",
        "economic_snapshot": {},
        "energy_snapshot": {},
        "forecast": ai_reasoning.get("forecast") or {
            "7d": "Monitor for short-term political, security, economic, and social stability shifts.",
            "30d": f"{country_name} remains under {risk_level} monitoring based on current analyst scoring and live signal activity.",
            "90d": "Medium-term outlook depends on convergence across political, military, economic, energy, and supply-chain indicators."
        },
        "decision_support": ai_reasoning.get("decision_support") or [
            "Monitor changes across top risk domains.",
            "Compare analyst score movement over time.",
            "Escalate to scenario simulation if military, energy, or supply-chain risk rises."
        ],
        "scenario_questions": ai_reasoning.get("scenario_questions") or [
            f"What happens if political stability deteriorates in {country_name}?",
            f"What happens if military activity increases around {country_name}?",
            f"What are the supply-chain implications of instability in {country_name}?"
        ],
        "model_used": ai_reasoning.get("model_used", "country_intelligence_v1_signals")
    }

    insert_res = (
        supabase.table("country_intelligence_reports")
        .insert(report)
        .execute()
    )

    returned = insert_res.data[0] if insert_res.data else report
    returned["signal_count"] = len(live_signals)
    returned["saved_signal_count"] = len(saved_signals)

    # Save report context for cross-module memory and scenario handoff
    try:
        memory_payload = {
            "source_module": "country_intelligence",
            "target_module": "scenario_analysis",
            "country_name": country_name,
            "iso3": iso3,
            "report_id": returned.get("id"),
            "selected_question": None,
            "context_payload": {
                "country_name": country_name,
                "iso3": iso3,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "executive_judgment": returned.get("executive_judgment"),
                "risk_context": returned.get("risk_context"),
                "strategic_signals": returned.get("strategic_signals", []),
                "signal_convergence": returned.get("signal_convergence"),
                "forecast": returned.get("forecast"),
                "strategic_recommendations": returned.get("decision_support", []),
                "scenario_questions": returned.get("scenario_questions", []),
                "created_at": returned.get("created_at")
            }
        }

        supabase.table("report_context_memory").insert(memory_payload).execute()
    except Exception:
        pass

    return {
        "status": "success",
        "data": returned
    }


@router.get("/{iso3}/reports")
def get_country_reports(iso3: str, limit: int = 10):
    require_supabase()

    iso3 = iso3.upper()

    res = (
        supabase.table("country_intelligence_reports")
        .select("*")
        .eq("iso3", iso3)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "status": "success",
        "count": len(res.data or []),
        "data": res.data or []
    }
