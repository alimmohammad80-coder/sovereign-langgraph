from fastapi import APIRouter
from app.services.global_risk_engine import get_global_risk_countries

router = APIRouter(
    prefix="/api/global-risk",
    tags=["Global Strategic Risk"],
)


@router.get("/countries")
def get_countries():
    data = get_global_risk_countries()
    return {
        "status": "success",
        "count": len(data),
        "data": data,
    }


@router.get("/summary")
def get_summary():
    data = get_global_risk_countries()
    return {
        "status": "success",
        "country_count": len(data),
        "critical": len([c for c in data if c.get("risk_level") == "Critical"]),
        "high": len([c for c in data if c.get("risk_level") == "High"]),
        "elevated": len([c for c in data if c.get("risk_level") == "Elevated"]),
        "guarded": len([c for c in data if c.get("risk_level") == "Guarded"]),
        "low": len([c for c in data if c.get("risk_level") == "Low"]),
    }


@router.get("/countries/{iso3}")
def get_country_by_iso3(iso3: str):
    iso3 = iso3.upper().strip()
    data = get_global_risk_countries()

    country = next((c for c in data if c.get("iso3") == iso3), None)

    if not country:
        return {
            "status": "error",
            "message": f"Country {iso3} not found",
            "data": None,
        }

    return {
        "status": "success",
        "data": country,
    }
