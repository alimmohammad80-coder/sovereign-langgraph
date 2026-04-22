from app.services.supabase_service import supabase

def normalize_news_articles(articles):
    rows = []
    for article in articles:
        rows.append({
            "source_name": article.get("source", {}).get("name", "newsapi"),
            "source_type": "news",
            "title": article.get("title"),
            "summary": article.get("description"),
            "url": article.get("url"),
            "country": None,
            "region": None,
            "topic": "geopolitics",
            "event_type": None,
            "severity_score": None,
            "confidence_score": 70,
            "published_at": article.get("publishedAt"),
            "raw_ref": article.get("url")
        })

    if not rows:
        return {"inserted": 0, "data": []}

    result = supabase.table("normalized_signals").insert(rows).execute()
    return {
        "inserted": len(rows),
        "data": result.data
    }
