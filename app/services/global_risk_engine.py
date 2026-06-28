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
        .select("iso3,name,region,latitude,longitude")
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
            "region": c.get("region"),
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
