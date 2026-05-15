from fastapi import APIRouter
from app.services.gdelt_service import fetch_gdelt_news
from app.services.gdelt_storage_service import save_raw_gdelt

router = APIRouter(
    prefix="/api/gdelt",
    tags=["GDELT"]
)

@router.get("/news")
def gdelt_news(query: str = "China Taiwan", max_records: int = 10):
    data = fetch_gdelt_news(
        query=query,
        max_records=max_records
    )

    if data["status"] == "success":
        try:
            storage = save_raw_gdelt(data["articles"])
            data["storage"] = storage
        except Exception as e:
            data["storage_error"] = str(e)

    return data
