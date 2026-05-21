import requests
import feedparser
from datetime import datetime
from urllib.parse import quote_plus


def fetch_google_news_supply_chain(country=None, sector=None, chokepoint=None, commodity=None, limit=8):
    query_parts = [x for x in [country, sector, chokepoint, commodity, "supply chain disruption"] if x]
    query = " ".join(query_parts)

    rss_url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )

    try:
        feed = feedparser.parse(rss_url)
        articles = []

        for entry in feed.entries[:limit]:
            source_title = None
            if hasattr(entry, "source") and isinstance(entry.source, dict):
                source_title = entry.source.get("title")

            articles.append({
                "source": "Google News RSS",
                "title": entry.get("title"),
                "url": entry.get("link"),
                "domain": source_title,
                "published_at": entry.get("published"),
                "summary": entry.get("summary"),
                "query": query
            })

        return articles

    except Exception as e:
        return [{
            "source": "Google News RSS",
            "error": str(e),
            "query": query,
            "published_at": datetime.utcnow().isoformat()
        }]


def fetch_gdelt_supply_chain_news(country=None, sector=None, chokepoint=None, commodity=None, limit=5):
    query_parts = [x for x in [country, sector, chokepoint, commodity, "supply chain disruption"] if x]
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
        response = requests.get(url, params=params, timeout=8)
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
        return [{
            "source": "GDELT",
            "error": str(e),
            "query": query,
            "published_at": datetime.utcnow().isoformat()
        }]


def fetch_live_supply_chain_sources(country=None, sector=None, chokepoint=None, commodity=None):
    google_news = fetch_google_news_supply_chain(
        country=country,
        sector=sector,
        chokepoint=chokepoint,
        commodity=commodity,
        limit=8
    )

    gdelt_news = fetch_gdelt_supply_chain_news(
        country=country,
        sector=sector,
        chokepoint=chokepoint,
        commodity=commodity,
        limit=5
    )

    combined_articles = []

    if google_news:
        combined_articles.extend(google_news)

    if gdelt_news and not gdelt_news[0].get("error"):
        combined_articles.extend(gdelt_news)

    return {
        "google_news": google_news,
        "gdelt_news": gdelt_news,
        "combined_articles": combined_articles,
        "source_status": {
            "google_news": "connected",
            "gdelt": "connected_with_fallback",
            "ofac": "planned",
            "eia": "planned",
            "world_bank": "planned",
            "maritime_ais": "planned"
        }
    }
