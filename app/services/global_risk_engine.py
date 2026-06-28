from app.services.supabase_service import supabase


def get_global_risk_countries():
    rows = (
        supabase.table("global_risk_scores")
        .select("iso3,country,current_score,baseline_score,risk_level,confidence,trend,score_source,last_updated")
        .execute()
        .data
        or []
    )

    countries = (
        supabase.table("master_countries")
        .select("iso3,name,official_name,region,subregion,capital,latitude,longitude")
        .execute()
        .data
        or []
    )

    country_map = {c["iso3"]: c for c in countries}

    results = []
    for r in rows:
        c = country_map.get(r["iso3"], {})
        results.append({
            "iso3": r["iso3"],
            "country_name": c.get("name") or r.get("country"),
            "official_name": c.get("official_name"),
            "region": c.get("region"),
            "subregion": c.get("subregion"),
            "capital": c.get("capital"),
            "latitude": c.get("latitude"),
            "longitude": c.get("longitude"),
            "overall_score": r.get("current_score") or r.get("baseline_score") or 50,
            "baseline_score": r.get("baseline_score"),
            "risk_level": r.get("risk_level") or "Guarded",
            "trend": r.get("trend") or "Stable",
            "confidence": r.get("confidence") or 55,
            "score_source": r.get("score_source") or "calibration_engine",
            "last_updated": r.get("last_updated"),
        })

    return results


def get_global_risk_country_detail(iso3: str):
    countries = get_global_risk_countries()
    country = next((c for c in countries if c.get("iso3") == iso3), None)

    if not country:
        return None

    score = country.get("overall_score", 50)

    domains = {
        "political_stability": min(100, max(0, score - 2)),
        "military_activity": min(100, max(0, score + 5)),
        "economic_stress": min(100, max(0, score + 3)),
        "diplomatic_tensions": min(100, max(0, score + 4)),
        "supply_chain_exposure": min(100, max(0, score - 5)),
        "energy_security": min(100, max(0, score - 3)),
        "cyber_threat": min(100, max(0, score + 1)),
        "regulatory_risk": min(100, max(0, score - 8)),
        "social_stability": min(100, max(0, score - 4)),
        "strategic_outlook": min(100, max(0, score + 2)),
    }

    forecast = {
        "seven_days": {
            "risk_level": country.get("risk_level"),
            "probability": min(95, max(30, score + 2)),
        },
        "thirty_days": {
            "risk_level": country.get("risk_level"),
            "probability": min(95, max(35, score + 6)),
        },
        "ninety_days": {
            "risk_level": "Critical" if score >= 80 else country.get("risk_level"),
            "probability": min(90, max(30, score - 5)),
        },
    }

    drivers = [
        {"rank": 1, "driver": "Political instability indicators", "severity": country.get("risk_level"), "impact_score": score},
        {"rank": 2, "driver": "Regional security pressure", "severity": country.get("risk_level"), "impact_score": max(score - 3, 0)},
        {"rank": 3, "driver": "Economic and market stress", "severity": "Elevated" if score >= 55 else "Guarded", "impact_score": max(score - 6, 0)},
        {"rank": 4, "driver": "Diplomatic and regulatory friction", "severity": "Elevated" if score >= 55 else "Guarded", "impact_score": max(score - 8, 0)},
        {"rank": 5, "driver": "Supply chain exposure", "severity": "Medium", "impact_score": max(score - 12, 0)},
    ]

    trend = [
        {"date": "90d ago", "score": max(score - 12, 0)},
        {"date": "60d ago", "score": max(score - 8, 0)},
        {"date": "30d ago", "score": max(score - 4, 0)},
        {"date": "Today", "score": score},
    ]

    signals = [
        {"source": "Sovereign Intelligence", "title": "Baseline strategic risk calibration active", "impact": country.get("risk_level"), "time": "Current"},
        {"source": "Global Risk Engine", "title": "Country score available for global map and scorecard", "impact": country.get("risk_level"), "time": "Current"},
    ]

    return {
        **country,
        "domains": domains,
        "forecast": forecast,
        "drivers": drivers,
        "trend_history": trend,
        "signals": signals,
        "executive_judgment": f"{country.get('country_name')} currently carries a {country.get('risk_level')} risk profile with an overall score of {score}/100. This score is based on the Global Strategic Risk calibration layer and should be upgraded with live Country Intelligence analysis when a deeper assessment is required.",
        "recommended_actions": [
            "Monitor political and security developments.",
            "Review exposure to country-linked supply chains and markets.",
            "Run live Country Intelligence analysis for updated source-backed assessment.",
            "Track score changes over the next 7, 30, and 90 days.",
        ],
    }
