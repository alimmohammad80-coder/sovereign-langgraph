import requests
from datetime import datetime


def fetch_gdelt_supply_chain_news(country=None, sector=None, chokepoint=None, commodity=None, limit=5):
    query_parts = []

    for item in [country, sector, chokepoint, commodity]:
        if item:
            query_parts.append(str(item))

    query_parts.append("supply chain disruption")

    query = " ".join(query_parts)

    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": limit,
        "sort": "HybridRel"
    }

    try:
        response = requests.get(url, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])

        return [
            {
                "source": "GDELT",
                "title": article.get("title"),
                "url": article.get("url"),
                "domain": article.get("domain"),
                "published_at": article.get("seendate"),
                "summary": article.get("title"),
                "query": query
            }
            for article in articles
        ]

    except Exception as e:
        return [
            {
                "source": "GDELT",
                "error": str(e),
                "query": query,
                "published_at": datetime.utcnow().isoformat()
            }
        ]


def fetch_live_supply_chain_sources(country=None, sector=None, chokepoint=None, commodity=None):
    gdelt_news = fetch_gdelt_supply_chain_news(
        country=country,
        sector=sector,
        chokepoint=chokepoint,
        commodity=commodity,
        limit=5
    )

    return {
        "gdelt_news": gdelt_news,
        "source_status": {
            "gdelt": "connected",
            "ofac": "planned",
            "eia": "planned",
            "world_bank": "planned",
            "maritime_ais": "planned"
        }
    }
