import requests
from datetime import datetime

from app.services.translation_service import translate_to_english

def is_url(text):
    return isinstance(text, str) and text.startswith(("http://", "https://"))


GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_gdelt_news(query="China Taiwan", max_records=10):

    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": max_records,
        "format": "json",
        "sort": "DateDesc"
    }

    response = requests.get(
        GDELT_DOC_API,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        return {
            "status": "error",
            "message": response.text
        }

    data = response.json()

    articles = []

    for article in data.get("articles", []):

        title = article.get("title")
        summary = article.get("socialimage") or ""

        translated_title = title
        translated_summary = ""

        articles.append({
            "title": title,
            "title_en": translated_title,
            "url": article.get("url"),
            "source": article.get("sourcecountry"),
            "domain": article.get("domain"),
            "language": article.get("language"),
            "seendate": article.get("seendate"),
            "summary": summary,
            "summary_en": translated_summary
        })

    return {
        "status": "success",
        "fetched_at": datetime.utcnow().isoformat(),
        "query": query,
        "article_count": len(articles),
        "articles": articles
    }
