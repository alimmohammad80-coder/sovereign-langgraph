from app.services.supabase_service import supabase


def get_risk_level(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 55:
        return "Elevated"
    if score >= 35:
        return "Guarded"
    return "Low"


def get_global_risk_countries():
    countries = supabase.table("countries").select("*").execute().data or []
    baselines = supabase.table("country_baseline_scores").select("*").execute().data or []
    live_scores = supabase.table("country_risk_scores").select("*").execute().data or []

    baseline_map = {b.get("iso3"): b for b in baselines if b.get("iso3")}

    live_map = {}
    for s in live_scores:
        iso3 = s.get("iso3")
        if iso3 and iso3 not in live_map:
            live_map[iso3] = s

    results = []

    for c in countries:
        iso3 = c.get("iso3")
        if not iso3:
            continue

        live = live_map.get(iso3)
        baseline = baseline_map.get(iso3)

        if live:
            score = live.get("overall_score", 50)
            source = "live_country_intelligence"
            risk_level = live.get("risk_level") or get_risk_level(score)
            trend = live.get("trend", "Stable")
            confidence = live.get("confidence", 70)
            last_updated = live.get("created_at") or live.get("updated_at")
        elif baseline:
            score = baseline.get("baseline_score", 50)
            source = "baseline"
            risk_level = baseline.get("baseline_risk_level") or get_risk_level(score)
            trend = baseline.get("baseline_trend", "Stable")
            confidence = baseline.get("baseline_confidence", 60)
            last_updated = baseline.get("calibrated_at")
        else:
            score = 50
            source = "default"
            risk_level = "Guarded"
            trend = "Stable"
            confidence = 50
            last_updated = None

        results.append({
            "iso3": iso3,
            "country_name": c.get("country_name") or c.get("name"),
            "region": c.get("region"),
            "latitude": c.get("latitude"),
            "longitude": c.get("longitude"),
            "overall_score": score,
            "risk_level": risk_level,
            "trend": trend,
            "confidence": confidence,
            "score_source": source,
            "last_updated": last_updated,
        })

    return results
