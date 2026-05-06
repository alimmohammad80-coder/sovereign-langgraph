import requests
from urllib.parse import quote


def fetch_gdelt_signals(query: str = "supply chain disruption", maxrecords: int = 20):
    encoded = quote(query)
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={encoded}"
        "&mode=artlist"
        "&format=json"
        f"&maxrecords={maxrecords}"
        "&sort=hybridrel"
    )

    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        data = r.json()
        articles = data.get("articles", [])

        return [
            {
                "source": "GDELT",
                "signal_type": "news_event_signal",
                "title": a.get("title"),
                "url": a.get("url"),
                "domain": a.get("domain"),
                "source_country": a.get("sourceCountry"),
                "published_at": a.get("seendate"),
                "severity_score": 6,
                "reliability_score": 6,
                "summary": f"GDELT article signal for query: {query}"
            }
            for a in articles
        ]

    except Exception as e:
        return [
            {
                "source": "GDELT",
                "signal_type": "news_event_signal",
                "title": "GDELT temporarily rate-limited",
                "url": None,
                "domain": "gdeltproject.org",
                "source_country": None,
                "published_at": None,
                "severity_score": 5,
                "reliability_score": 5,
                "summary": f"GDELT live signal unavailable: {str(e)}"
            }
        ]
