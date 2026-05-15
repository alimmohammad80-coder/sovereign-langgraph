from fastapi import APIRouter
from app.services.risk_signal_service import generate_risk_signals

router = APIRouter(
    prefix="/api/risk",
    tags=["Risk Signals"]
)

@router.post("/generate")
def generate():
    try:
        return generate_risk_signals()
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
