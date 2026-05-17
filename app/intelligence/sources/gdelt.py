import requests
from typing import List, Dict, Any
from urllib.parse import quote_plus


def fetch_gdelt_news(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    encoded_query = quote_plus(query)

    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={encoded_query}"
        "&mode=artlist"
        "&format=json"
        f"&maxrecords={limit}"
        "&sort=hybridrel"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])
        items = []

        for article in articles[:limit]:
            items.append({
                "title": article.get("title") or "Untitled GDELT signal",
                "summary": article.get("seendate") or "",
                "source": article.get("domain") or "GDELT",
                "url": article.get("url"),
                "published_at": article.get("seendate"),
                "domain": "gdelt_live_news",
            })

        return items

    except Exception:
        # Do not return failed fetches as intelligence signals.
        # This prevents API errors/rate limits from polluting GPT analysis.
        return []
