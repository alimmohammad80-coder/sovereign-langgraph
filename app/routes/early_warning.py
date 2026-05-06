from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import requests
import math

router = APIRouter(prefix="/api/early-warning", tags=["Strategic Early Warning System"])


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

    for signal in signals:
        text = f"{signal.get('title', '')} {signal.get('summary', '')}".lower()

        severity = 20
        velocity = 20
        confidence = 50

        high_terms = [
            "attack", "strike", "missile", "war", "invasion", "sanctions",
            "mobilization", "military", "explosion", "terror", "cyberattack",
            "blockade", "coup", "riot", "crisis", "collapse"
        ]

        medium_terms = [
            "tension", "warning", "dispute", "protest", "threat",
            "pressure", "border", "naval", "drone", "election",
            "instability", "shortage", "disruption"
        ]

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

    severity_avg = severity_total / n
    velocity_avg = velocity_total / n
    confidence_avg = confidence_total / n

    final_score = int((severity_avg * 0.45) + (velocity_avg * 0.30) + (confidence_avg * 0.25))

    return max(0, min(final_score, 100))


def fetch_gdelt_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": maxrecords,
            "sort": "hybridrel"
        }

        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])

        return [
            {
                "title": article.get("title", "Untitled signal"),
                "summary": article.get("seendate", ""),
                "url": article.get("url"),
                "source": article.get("sourceCountry", "GDELT"),
                "published_at": article.get("seendate"),
                "domain": article.get("domain"),
                "category": "open-source signal"
            }
            for article in articles
        ]

    except Exception as e:
        return [
            {
                "title": "External signal fetch limited",
                "summary": f"GDELT request unavailable or rate-limited: {str(e)}",
                "source": "system",
                "category": "system_notice"
            }
        ]


def generate_indicators(country: str, topic: str, signals: List[Dict[str, Any]]) -> List[str]:
    base = [
        f"Increase in reporting volume related to {topic} in {country}",
        "Shift from routine political rhetoric to coercive or operational language",
        "Movement from isolated incidents toward repeated or clustered events",
        "Emergence of cross-domain indicators involving security, energy, cyber, or economic pressure",
        "Growing mismatch between official statements and observable behavior"
    ]

    if signals:
        base.append("Multiple open-source signals require corroboration against structured datasets")

    return base


def generate_scenarios(country: str, warning_level: str, topic: str) -> List[Dict[str, str]]:
    return [
        {
            "scenario": "Baseline Continuity",
            "description": f"{country} remains under observation with limited escalation, but signals continue to accumulate around {topic}.",
            "probability": "Medium",
            "impact": "Moderate"
        },
        {
            "scenario": "Accelerated Deterioration",
            "description": f"Warning indicators intensify, creating a higher-risk environment for security, markets, diplomacy, or operations in {country}.",
            "probability": "Medium-Low" if warning_level in ["Low", "Watch"] else "Medium-High",
            "impact": "High"
        },
        {
            "scenario": "Strategic Shock",
            "description": f"A triggering event produces rapid escalation, forcing government, corporate, or investor reassessment of exposure to {country}.",
            "probability": "Low" if warning_level in ["Low", "Watch"] else "Medium",
            "impact": "Severe"
        }
    ]


@router.get("/health")
def early_warning_health():
    return {
        "status": "online",
        "module": "Strategic Early Warning System",
        "version": "early-warning-system-v1",
        "timestamp": datetime.utcnow().isoformat()
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

    return {
        "engine": "sovereign_strategic_early_warning_system",
        "status": "success",
        "country": country,
        "region": request.region,
        "topic": topic,
        "timeframe": request.timeframe,
        "timestamp": datetime.utcnow().isoformat(),
        "warning_score": score,
        "warning_level": warning_level,
        "executive_judgment": (
            f"{country} currently registers a {warning_level.lower()} strategic warning posture "
            f"for {topic}. The assessment is based on open-source signal density, escalation language, "
            f"cross-domain indicators, and the velocity of reported developments. This should be treated "
            f"as an early-warning product, not a final intelligence assessment."
        ),
        "key_signals": signals,
        "early_warning_indicators": indicators,
        "drivers": [
            "Escalatory political or military language",
            "Open-source reporting density",
            "Potential cross-domain spillover",
            "Regional or market sensitivity",
            "Uncertainty around adversary intent and capability"
        ],
        "intelligence_gaps": [
            "Need corroboration from structured conflict datasets",
            "Need baseline comparison against historical incident frequency",
            "Need source reliability weighting",
            "Need geospatial event clustering",
            "Need human analyst validation for high-impact warnings"
        ],
        "scenarios": scenarios,
        "recommended_monitoring": [
            "Track changes in warning score over the next 24–72 hours",
            "Compare media signals with ACLED/GDELT event data",
            "Monitor sanctions, cyber, military, and energy indicators",
            "Escalate to analyst review if score rises above 70",
            "Generate country-specific exposure report for affected assets or portfolios"
        ]
    }


@router.get("/dashboard")
def early_warning_dashboard(
    country: str = Query("Global"),
    topic: str = Query("geopolitical risk")
):
    query = f"{country} {topic} warning crisis escalation"
    signals = fetch_gdelt_signals(query=query, maxrecords=6)

    score = calculate_warning_score(signals)
    level = classify_warning_level(score)

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
            "last_updated": datetime.utcnow().isoformat()
        },
        "warning_layers": [
            {
                "name": "Geopolitical Warning",
                "score": score,
                "status": level
            },
            {
                "name": "Security Instability",
                "score": max(20, score - 5),
                "status": classify_warning_level(max(20, score - 5))
            },
            {
                "name": "Economic Exposure",
                "score": max(15, score - 12),
                "status": classify_warning_level(max(15, score - 12))
            },
            {
                "name": "Energy/Supply Chain Spillover",
                "score": max(10, score - 8),
                "status": classify_warning_level(max(10, score - 8))
            },
            {
                "name": "Cyber/Information Risk",
                "score": max(10, score - 15),
                "status": classify_warning_level(max(10, score - 15))
            }
        ],
        "signals": signals
    }


@router.get("/global-watchlist")
def global_watchlist():
    countries = [
        "China Taiwan Strait",
        "Iran Strait of Hormuz",
        "Russia Ukraine",
        "Pakistan India",
        "Red Sea shipping",
        "North Korea missile",
        "Venezuela political crisis"
    ]

    watchlist = []

    for item in countries:
        signals = fetch_gdelt_signals(f"{item} warning escalation crisis", maxrecords=4)
        score = calculate_warning_score(signals)

        watchlist.append({
            "area": item,
            "warning_score": score,
            "warning_level": classify_warning_level(score),
            "active_signals": len(signals),
            "summary": f"{item} is under automated monitoring for escalation, instability, and strategic disruption."
        })

    return {
        "module": "Global Strategic Watchlist",
        "timestamp": datetime.utcnow().isoformat(),
        "watchlist": sorted(watchlist, key=lambda x: x["warning_score"], reverse=True)
    }
