from fastapi import APIRouter
from app.services.fusion_signal_service import generate_fusion_report

router = APIRouter(
    prefix="/api/fusion",
    tags=["Fusion"]
)

@router.get("/from-signals")
def fusion(country: str = "China"):

    return generate_fusion_report(country=country)
