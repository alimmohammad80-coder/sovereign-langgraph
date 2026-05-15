from fastapi import APIRouter
from app.services.google_news_service import fetch_google_news
from app.services.gdelt_storage_service import save_raw_gdelt

router = APIRouter(
    prefix="/api/news",
    tags=["News"]
)

@router.get("/google")
def google_news(query: str = "China", max_records: int = 5):
    data = fetch_google_news(query=query, max_records=max_records)

    try:
        storage = save_raw_gdelt(data["articles"])
        data["storage"] = storage
    except Exception as e:
        data["storage_error"] = str(e)

    return data
