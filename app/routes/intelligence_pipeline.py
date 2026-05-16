from fastapi import APIRouter
from app.intelligence.schemas import IntelligenceIndicatorRequest
from app.intelligence.pipeline import run_intelligence_pipeline
from app.intelligence.sources.google_news import fetch_google_news

router = APIRouter(
    prefix="/api/intelligence",
    tags=["Unified Intelligence Pipeline"]
)


@router.post("/run-indicator")
def run_indicator(payload: IntelligenceIndicatorRequest):
    query = f"{payload.entity} {payload.indicator}"

    raw_items = fetch_google_news(
        query=query,
        limit=payload.limit
    )

    return run_intelligence_pipeline(
        module=payload.module,
        entity=payload.entity,
        indicator=payload.indicator,
        raw_items=raw_items,
    )
