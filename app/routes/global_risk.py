from fastapi import APIRouter, HTTPException
from app.services.global_risk_engine import (
    get_global_risk_countries,
    get_global_risk_country_detail,
)

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


@router.get("/countries/{iso3}")
def get_country_detail(iso3: str):
    data = get_global_risk_country_detail(iso3.upper().strip())

    if not data:
        raise HTTPException(status_code=404, detail=f"Country {iso3} not found")

    return {
        "status": "success",
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
