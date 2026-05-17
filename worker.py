import time

from app.intelligence.sources.google_news import fetch_google_news
from app.intelligence.sources.gdelt import fetch_gdelt_news
from app.intelligence.pipeline import run_intelligence_pipeline


WATCHLIST = [
    {
        "module": "strategic_early_warning",
        "entity": "China",
        "indicator": "Taiwan Strait Military Pressure"
    },
    {
        "module": "supply_chain",
        "entity": "Red Sea",
        "indicator": "Maritime Shipping Disruption"
    },
    {
        "module": "financial_risk",
        "entity": "United States",
        "indicator": "Banking Sector Stress"
    }
]


def run_watchlist_once():
    print("Running Sovereign Intelligence pipeline...")

    for item in WATCHLIST:
        try:
            query = f"{item['entity']} {item['indicator']}"

            google_items = fetch_google_news(query=query, limit=5)
            gdelt_items = fetch_gdelt_news(query=query, limit=5)

            raw_items = google_items + gdelt_items

            result = run_intelligence_pipeline(
                module=item["module"],
                entity=item["entity"],
                indicator=item["indicator"],
                raw_items=raw_items,
            )

            print(
                f"Completed: {item['entity']} - {item['indicator']} | "
                f"Score: {result.get('score')} | Level: {result.get('level')}"
            )

        except Exception as e:
            print(f"ERROR running {item['entity']} - {item['indicator']}: {e}")


if __name__ == "__main__":
    while True:
        run_watchlist_once()
        time.sleep(1800)
