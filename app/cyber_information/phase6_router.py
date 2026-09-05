from fastapi import APIRouter

from .forecast_engine import CyberHybridForecastEngine
from .phase6_models import ForecastRequest

router = APIRouter(
    prefix="/api/cyber-information/forecasting",
    tags=["Cyber & Information Forecasting"],
)
engine = CyberHybridForecastEngine()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "phase": 6,
        "module": "cyber_hybrid_forecasting",
        "formula_version": "cyber-hybrid-logit-v1",
        "horizons": ["7d", "30d", "90d"],
        "calibration_status": "baseline_requires_historical_calibration",
    }


@router.post("/forecast")
def forecast(request: ForecastRequest) -> dict:
    result = engine.forecast(request)
    return {"status": "success", "data": result.model_dump(mode="json")}


@router.post("/early-warning-handoff")
def early_warning_handoff(request: ForecastRequest) -> dict:
    result = engine.forecast(request)
    return {"status": "success", "data": engine.to_early_warning_handoff(result)}
