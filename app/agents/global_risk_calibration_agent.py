from app.services.supabase_service import supabase

RISK_LEVELS = [
    (85, "Critical"),
    (70, "High"),
    (55, "Elevated"),
    (35, "Guarded"),
    (0, "Low"),
]

def risk_level(score: int) -> str:
    for threshold, level in RISK_LEVELS:
        if score >= threshold:
            return level
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
    return "Stable"

def calibrate_existing_countries():
    countries = supabase.table("countries").select("iso3,name,country_name,region").execute().data or []

    rows = []
    for c in countries:
        iso3 = c.get("iso3")
        if not iso3:
            continue

        score = COUNTRY_BASELINES.get(iso3, 50)

        rows.append({
            "iso3": iso3,
            "baseline_score": score,
            "baseline_risk_level": risk_level(score),
            "baseline_confidence": 70 if score != 50 else 55,
            "baseline_trend": trend_for_score(score),
        })

    if rows:
        supabase.table("country_baseline_scores").upsert(rows, on_conflict="iso3").execute()

    print(f"Calibrated {len(rows)} countries.")

if __name__ == "__main__":
    calibrate_existing_countries()
