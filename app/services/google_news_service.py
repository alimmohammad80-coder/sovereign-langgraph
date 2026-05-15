import feedparser
from urllib.parse import quote_plus
from datetime import datetime

def fetch_google_news(query="China", max_records=5):
    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)

    articles = []

    for entry in feed.entries[:max_records]:
        articles.append({
            "title": entry.get("title"),
            "title_en": entry.get("title"),
            "url": entry.get("link"),
            "source": "Google News RSS",
            "domain": "news.google.com",
            "language": "English",
            "seendate": entry.get("published"),
            "summary": entry.get("summary", ""),
            "summary_en": entry.get("summary", "")
        })

    return {
        "status": "success",
        "provider": "google_news_rss",
        "fetched_at": datetime.utcnow().isoformat(),
        "query": query,
        "article_count": len(articles),
        "articles": articles
    }
