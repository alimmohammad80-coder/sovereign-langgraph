from fastapi import APIRouter, Query
from app.services.ingestion.news_ingestion import run_google_news_ingestion

router = APIRouter(prefix="/api/ingestion", tags=["Ingestion"])


@router.get("/health")
def ingestion_health():
    return {
        "status": "ok",
        "service": "live_signal_ingestion",
        "purpose": "Fetch live news/events and store them as risk_signals."
    }


@router.post("/run-news")
def run_news_ingestion(limit_per_topic: int = Query(5, ge=1, le=20)):
    return run_google_news_ingestion(limit_per_topic=limit_per_topic)
