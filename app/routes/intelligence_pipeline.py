from fastapi import APIRouter

from app.intelligence.schemas import IntelligenceIndicatorRequest
from app.intelligence.pipeline import run_intelligence_pipeline

from app.intelligence.sources.google_news import fetch_google_news
from app.intelligence.sources.gdelt import fetch_gdelt_news


router = APIRouter(
    prefix="/api/intelligence",
    tags=["Unified Intelligence Pipeline"]
)


@router.post("/run-indicator")
def run_indicator(payload: IntelligenceIndicatorRequest):

    query = f"{payload.entity} {payload.indicator}"

    google_items = fetch_google_news(
        query=query,
        limit=payload.limit
    )

    gdelt_items = fetch_gdelt_news(
        query=query,
        limit=payload.limit
    )

    raw_items = google_items + gdelt_items

    return run_intelligence_pipeline(
        module=payload.module,
        entity=payload.entity,
        indicator=payload.indicator,
        raw_items=raw_items,
    )
