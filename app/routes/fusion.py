from fastapi import APIRouter
from pydantic import BaseModel
from app.services.openai_fusion import generate_fusion_report

router = APIRouter(prefix="/api/fusion", tags=["Fusion Intelligence"])

class FusionRequest(BaseModel):
    country: str
    signals: list
    sources: list

@router.post("/full-briefing")
def full_briefing(payload: FusionRequest):
    report = generate_fusion_report(
        country=payload.country,
        signals=payload.signals,
        sources=payload.sources
    )
    return {
        "status": "success",
        "engine": "gpt-5.5-fusion",
        "country": payload.country,
        "report": report
    }
