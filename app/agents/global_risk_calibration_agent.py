from app.services.supabase_service import supabase

def risk_level(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 55:
        return "Elevated"
    if score >= 35:
        return "Guarded"
    return "Low"

COUNTRY_BASELINES = {
    "AFG": 78, "CHN": 68, "RUS": 82, "IRN": 76, "UKR": 88,
    "PAK": 72, "IND": 52, "TWN": 74, "ISR": 79, "SAU": 55,
    "TUR": 59, "USA": 38, "DEU": 34, "FRA": 39, "GBR": 37,
    "JPN": 36, "KOR": 43, "PRK": 86, "CAN": 28, "MEX": 58,
    "BRA": 49, "OMN": 42, "EGY": 61
}

def trend_for_score(score: int) -> str:
    if score >= 70:
        return "Deteriorating"
    if score >= 55:
        return "Elevated"
    return "Stable"

def calibrate_master_countries():
    countries = supabase.table("master_countries").select("iso3,name,region").execute().data or []

    rows = []
    for c in countries:
        iso3 = c.get("iso3")
        name = c.get("name")
        if not iso3:
            continue

        score = COUNTRY_BASELINES.get(iso3, 50)

        rows.append({
            "country": name,
            "iso3": iso3,
            "risk_score": score,
            "risk_category": risk_level(score),
            "baseline_score": score,
            "current_score": score,
            "risk_level": risk_level(score),
            "confidence": 70 if score != 50 else 55,
            "trend": trend_for_score(score),
            "score_source": "calibration_engine",
        })

    if rows:
        supabase.table("global_risk_scores").upsert(rows, on_conflict="iso3").execute()

    print(f"Calibrated {len(rows)} countries.")

if __name__ == "__main__":
    calibrate_master_countries()
