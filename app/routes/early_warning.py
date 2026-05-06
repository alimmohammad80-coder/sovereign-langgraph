from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import requests

try:
    from supabase import create_client
except Exception as e:
    create_client = None
    print(f"[Early Warning] Supabase import unavailable: {e}")


router = APIRouter(
    prefix="/api/early-warning",
    tags=["Strategic Early Warning System"]
)


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if create_client and SUPABASE_URL and SUPABASE_KEY
    else None
)

if supabase:
    print("[Early Warning] Supabase configured.")
else:
    print("[Early Warning] Supabase not configured or unavailable.")


class WarningRequest(BaseModel):
    country: Optional[str] = "Global"
    region: Optional[str] = None
    topic: Optional[str] = "geopolitical risk"
    timeframe: Optional[str] = "30 days"
    include_scenarios: Optional[bool] = True


def classify_warning_level(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 50:
        return "Elevated"
    if score >= 30:
        return "Watch"
    return "Low"


def calculate_warning_score(signals: List[Dict[str, Any]]) -> int:
    if not signals:
        return 35

    severity_total = 0
    velocity_total = 0
    confidence_total = 0

    high_terms = [
        "attack", "strike", "missile", "war", "invasion", "sanctions",
        "mobilization", "military", "explosion", "terror", "cyberattack",
        "blockade", "coup", "riot", "crisis", "collapse", "nuclear",
        "escalation", "airstrike", "drone", "shipping attack", "oil disruption"
    ]

    medium_terms = [
        "tension", "warning", "dispute", "protest", "threat", "pressure",
        "border", "naval", "election", "instability", "shortage",
        "disruption", "militia", "embargo", "closure", "exercise"
    ]

    for signal in signals:
        text = f"{signal.get('title', '')} {signal.get('summary', '')}".lower()

        severity = 20
        velocity = 20
        confidence = 50

        for term in high_terms:
            if term in text:
                severity += 8
                velocity += 5
                confidence += 3

        for term in medium_terms:
            if term in text:
                severity += 4
                velocity += 3
                confidence += 2

        severity_total += min(severity, 100)
        velocity_total += min(velocity, 100)
        confidence_total += min(confidence, 95)

    n = len(signals)

    final_score = int(
        ((severity_total / n) * 0.45)
        + ((velocity_total / n) * 0.30)
        + ((confidence_total / n) * 0.25)
    )

    return max(0, min(final_score, 100))


def fetch_gdelt_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": maxrecords,
            "sort": "hybridrel",
        }

        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])

        if not articles:
            return [
                {
                    "title": "No live external signals returned",
                    "summary": "The external source returned no current articles for this query.",
                    "source": "system",
                    "domain": None,
                    "url": None,
                    "published_at": datetime.utcnow().isoformat(),
                    "category": "system_notice",
                    "signal_type": "system_notice",
                }
            ]

        return [
            {
                "title": article.get("title") or "Untitled signal",
                "summary": article.get("seendate") or "",
                "url": article.get("url"),
                "source": article.get("sourceCountry") or "GDELT",
                "published_at": article.get("seendate"),
                "domain": article.get("domain"),
                "category": "open_source_signal",
                "signal_type": "news_signal",
            }
            for article in articles
        ]

    except Exception as e:
        return [
            {
                "title": "External signal fetch limited",
                "summary": f"GDELT request unavailable or rate-limited: {str(e)}",
                "source": "system",
                "domain": None,
                "url": None,
                "published_at": datetime.utcnow().isoformat(),
                "category": "system_notice",
                "signal_type": "system_notice",
            }
        ]


def build_warning_layers(score: int) -> List[Dict[str, Any]]:
    return [
        {
            "name": "Geopolitical Warning",
            "score": score,
            "status": classify_warning_level(score),
            "explanation": "Measures political, diplomatic, military, and interstate escalation pressure.",
        },
        {
            "name": "Security Instability",
            "score": max(20, score - 5),
            "status": classify_warning_level(max(20, score - 5)),
            "explanation": "Measures conflict, terrorism, unrest, protest, military activity, and internal security risk.",
        },
        {
            "name": "Economic Exposure",
            "score": max(15, score - 12),
            "status": classify_warning_level(max(15, score - 12)),
            "explanation": "Measures sanctions, market disruption, investor exposure, inflation pressure, and fiscal stress.",
        },
        {
            "name": "Energy/Supply Chain Spillover",
            "score": max(10, score - 8),
            "status": classify_warning_level(max(10, score - 8)),
            "explanation": "Measures chokepoint risk, shipping disruption, energy flows, commodity exposure, and trade disruption.",
        },
        {
            "name": "Cyber/Information Risk",
            "score": max(10, score - 15),
            "status": classify_warning_level(max(10, score - 15)),
            "explanation": "Measures cyber escalation, disinformation, information warfare, and digital infrastructure risk.",
        },
    ]


def generate_indicators(country: str, topic: str, signals: List[Dict[str, Any]]) -> List[str]:
    indicators = [
        f"Increase in reporting volume related to {topic} in {country}",
        "Shift from routine political rhetoric to coercive or operational language",
        "Movement from isolated incidents toward repeated or clustered events",
        "Emergence of cross-domain indicators involving security, energy, cyber, or economic pressure",
        "Growing mismatch between official statements and observable behavior",
    ]

    if signals:
        indicators.append("Multiple open-source signals require corroboration against structured datasets")

    return indicators


def generate_scenarios(country: str, warning_level: str, topic: str) -> List[Dict[str, str]]:
    return [
        {
            "scenario": "Baseline Continuity",
            "description": f"{country} remains under observation with limited escalation, but signals continue to accumulate around {topic}.",
            "probability": "Medium",
            "impact": "Moderate",
            "strategic_implication": "Decision-makers should continue monitoring but avoid overreacting without corroborated indicators.",
        },
        {
            "scenario": "Accelerated Deterioration",
            "description": f"Warning indicators intensify, creating a higher-risk environment for security, markets, diplomacy, or operations in {country}.",
            "probability": "Medium-Low" if warning_level in ["Low", "Watch"] else "Medium-High",
            "impact": "High",
            "strategic_implication": "Organizations should review exposure, contingency plans, dependencies, and escalation thresholds.",
        },
        {
            "scenario": "Strategic Shock",
            "description": f"A triggering event produces rapid escalation, forcing government, corporate, or investor reassessment of exposure to {country}.",
            "probability": "Low" if warning_level in ["Low", "Watch"] else "Medium",
            "impact": "Severe",
            "strategic_implication": "Rapid decision support, executive notification, and crisis-response protocols may be required.",
        },
    ]


def save_early_warning_run(result: Dict[str, Any]) -> Optional[str]:
    if not supabase:
        return None

    try:
        run_payload = {
            "country": result.get("country"),
            "region": result.get("region"),
            "topic": result.get("topic"),
            "timeframe": result.get("timeframe"),
            "warning_score": result.get("warning_score"),
            "warning_level": result.get("warning_level"),
            "executive_judgment": result.get("executive_judgment"),
            "engine": result.get("engine"),
            "status": result.get("status"),
            "confidence_score": result.get("confidence_score", 60),
        }

        run_response = supabase.table("early_warning_runs").insert(run_payload).execute()

        if not run_response.data:
            print("[Early Warning] Supabase run insert returned no data.")
            return None

        run_id = run_response.data[0]["id"]

        for signal in result.get("key_signals", []):
            supabase.table("early_warning_signals").insert(
                {
                    "run_id": run_id,
                    "title": signal.get("title") or "Untitled signal",
                    "summary": signal.get("summary"),
                    "source": signal.get("source"),
                    "domain": signal.get("domain"),
                    "url": signal.get("url"),
                    "published_at": signal.get("published_at"),
                    "category": signal.get("category"),
                    "signal_type": signal.get("signal_type"),
                    "country": result.get("country"),
                    "region": result.get("region"),
                    "severity_score": signal.get("severity_score", 50),
                    "reliability_score": signal.get("reliability_score", 50),
                    "relevance_score": signal.get("relevance_score", 50),
                }
            ).execute()

        for layer in result.get("warning_layers", []):
            supabase.table("early_warning_layers").insert(
                {
                    "run_id": run_id,
                    "layer_name": layer.get("name"),
                    "layer_score": layer.get("score"),
                    "layer_status": layer.get("status"),
                    "explanation": layer.get("explanation"),
                }
            ).execute()

        for indicator in result.get("early_warning_indicators", []):
            supabase.table("early_warning_indicators").insert(
                {
                    "run_id": run_id,
                    "indicator": indicator,
                    "status": "Monitoring",
                    "relevance": "Medium",
                    "analyst_note": "Automatically generated indicator requiring analyst validation.",
                }
            ).execute()

        for scenario in result.get("scenarios", []):
            supabase.table("early_warning_scenarios").insert(
                {
                    "run_id": run_id,
                    "scenario_name": scenario.get("scenario"),
                    "description": scenario.get("description"),
                    "probability": scenario.get("probability"),
                    "impact": scenario.get("impact"),
                    "strategic_implication": scenario.get("strategic_implication"),
                }
            ).execute()

        supabase.table("warning_score_history").insert(
            {
                "area": result.get("country") or "Global",
                "country": result.get("country"),
                "region": result.get("region"),
                "topic": result.get("topic"),
                "warning_score": result.get("warning_score"),
                "warning_level": result.get("warning_level"),
                "source_run_id": run_id,
            }
        ).execute()

        return run_id

    except Exception as e:
        print(f"[Early Warning] Supabase save error: {e}")
        return None


@router.get("/health")
def early_warning_health():
    return {
        "status": "online",
        "module": "Strategic Early Warning System",
        "version": "early-warning-system-v2-supabase",
        "supabase_configured": True if supabase else False,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/run")
def run_early_warning_agent(request: WarningRequest):
    country = request.country or "Global"
    topic = request.topic or "geopolitical risk"

    query = f"{country} {topic} crisis warning security escalation"
    signals = fetch_gdelt_signals(query=query, maxrecords=10)

    score = calculate_warning_score(signals)
    warning_level = classify_warning_level(score)

    indicators = generate_indicators(country, topic, signals)
    scenarios = generate_scenarios(country, warning_level, topic) if request.include_scenarios else []
    warning_layers = build_warning_layers(score)

    result = {
        "engine": "sovereign_strategic_early_warning_system",
        "status": "success",
        "country": country,
        "region": request.region,
        "topic": topic,
        "timeframe": request.timeframe,
        "timestamp": datetime.utcnow().isoformat(),
        "warning_score": score,
        "warning_level": warning_level,
        "confidence_score": 60,
        "executive_judgment": (
            f"{country} currently registers a {warning_level.lower()} strategic warning posture "
            f"for {topic}. The assessment is based on open-source signal density, escalation language, "
            f"cross-domain indicators, and the velocity of reported developments. This should be treated "
            f"as an early-warning product, not a final intelligence assessment."
        ),
        "warning_layers": warning_layers,
        "key_signals": signals,
        "early_warning_indicators": indicators,
        "drivers": [
            "Escalatory political or military language",
            "Open-source reporting density",
            "Potential cross-domain spillover",
            "Regional or market sensitivity",
            "Uncertainty around adversary intent and capability",
        ],
        "intelligence_gaps": [
            "Need corroboration from structured conflict datasets",
            "Need baseline comparison against historical incident frequency",
            "Need source reliability weighting",
            "Need geospatial event clustering",
            "Need human analyst validation for high-impact warnings",
        ],
        "scenarios": scenarios,
        "recommended_monitoring": [
            "Track changes in warning score over the next 24–72 hours",
            "Compare media signals with ACLED/GDELT event data",
            "Monitor sanctions, cyber, military, and energy indicators",
            "Escalate to analyst review if score rises above 70",
            "Generate country-specific exposure report for affected assets or portfolios",
        ],
    }

    run_id = save_early_warning_run(result)

    result["supabase_run_id"] = run_id
    result["saved_to_supabase"] = True if run_id else False

    return result


@router.get("/dashboard")
def early_warning_dashboard(
    country: str = Query("Global"),
    topic: str = Query("geopolitical risk"),
):
    query = f"{country} {topic} warning crisis escalation"
    signals = fetch_gdelt_signals(query=query, maxrecords=6)

    score = calculate_warning_score(signals)
    level = classify_warning_level(score)
    warning_layers = build_warning_layers(score)

    return {
        "module": "Strategic Early Warning Dashboard",
        "country": country,
        "topic": topic,
        "warning_score": score,
        "warning_level": level,
        "summary": {
            "active_signals": len(signals),
            "priority": level,
            "watch_status": "Active Watch" if score >= 50 else "Routine Monitoring",
            "last_updated": datetime.utcnow().isoformat(),
        },
        "warning_layers": warning_layers,
        "signals": signals,
    }


@router.get("/global-watchlist")
def global_watchlist():
    monitored_areas = [
        {"area": "Taiwan Strait", "country": "China/Taiwan", "region": "Indo-Pacific", "topic": "Taiwan Strait escalation risk"},
        {"area": "Strait of Hormuz", "country": "Iran", "region": "Middle East", "topic": "Energy chokepoint and military escalation risk"},
        {"area": "Red Sea Shipping Corridor", "country": "Yemen/Red Sea", "region": "Middle East / Africa", "topic": "Shipping disruption and maritime security risk"},
        {"area": "Russia-Ukraine War Zone", "country": "Ukraine", "region": "Europe", "topic": "Military escalation and European security risk"},
        {"area": "India-Pakistan Crisis Corridor", "country": "India/Pakistan", "region": "South Asia", "topic": "Border escalation and nuclear signaling risk"},
        {"area": "Korean Peninsula", "country": "North Korea/South Korea", "region": "East Asia", "topic": "Missile nuclear and military escalation risk"},
        {"area": "Venezuela Political Crisis", "country": "Venezuela", "region": "Latin America", "topic": "Political instability and regional spillover risk"},
    ]

    watchlist = []

    for item in monitored_areas:
        query = f"{item['country']} {item['topic']} warning escalation crisis"
        signals = fetch_gdelt_signals(query=query, maxrecords=4)
        score = calculate_warning_score(signals)

        watchlist.append(
            {
                "area": item["area"],
                "country": item["country"],
                "region": item["region"],
                "topic": item["topic"],
                "warning_score": score,
                "warning_level": classify_warning_level(score),
                "active_signals": len(signals),
                "summary": f"{item['area']} is under automated monitoring for escalation, instability, strategic disruption, and cross-domain spillover.",
            }
        )

    return {
        "module": "Global Strategic Watchlist",
        "timestamp": datetime.utcnow().isoformat(),
        "watchlist": sorted(watchlist, key=lambda x: x["warning_score"], reverse=True),
    }


@router.get("/recent-runs")
def get_recent_early_warning_runs(limit: int = Query(10, ge=1, le=50)):
    if not supabase:
        return {
            "status": "unavailable",
            "message": "Supabase is not configured.",
            "runs": [],
        }

    try:
        response = (
            supabase.table("early_warning_runs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return {
            "status": "success",
            "runs": response.data or [],
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "runs": [],
        }


@router.get("/score-history")
def get_warning_score_history(
    area: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    if not supabase:
        return {
            "status": "unavailable",
            "message": "Supabase is not configured.",
            "history": [],
        }

    try:
        query = (
            supabase.table("warning_score_history")
            .select("*")
            .order("recorded_at", desc=True)
            .limit(limit)
        )

        if area:
            query = query.eq("area", area)

        response = query.execute()

        return {
            "status": "success",
            "area": area,
            "history": response.data or [],
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "history": [],
        }
