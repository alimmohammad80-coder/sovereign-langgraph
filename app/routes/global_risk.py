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
