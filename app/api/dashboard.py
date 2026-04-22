from fastapi import APIRouter
from app.services.dashboard_service import build_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/test")
def test_dashboard():
    return {"status": "dashboard route working"}

@router.get("/overview")
def dashboard_overview(limit: int = 10, query: str | None = None):
    return build_dashboard_overview(limit=limit, query=query)
