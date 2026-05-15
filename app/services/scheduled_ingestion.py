import time
from app.services.gdelt_service import fetch_gdelt_news
from app.services.gdelt_storage_service import save_raw_gdelt

TOPICS = [
    "Russia Ukraine",
    "Red Sea shipping",
    "sanctions",
    "oil supply disruption"
]

def run_scheduled_ingestion():
    results = []

    for topic in TOPICS:
        data = fetch_gdelt_news(query=topic, max_records=1)

        if data.get("status") == "success":
            storage = save_raw_gdelt(data.get("articles", []))
            results.append({
                "topic": topic,
                "status": "success",
                "articles": len(data.get("articles", [])),
                "storage": storage
            })
        else:
            results.append({
                "topic": topic,
                "status": "error",
                "message": data.get("message")
            })

        time.sleep(15)

    return results
