from app.services.supabase_service import supabase

def normalize_gdelt_articles(articles):
    rows = []
    for article in articles:
        rows.append({
            "source_name": "gdelt",
            "source_type": "news",
            "title": article.get("title"),
            "summary": None,
            "url": article.get("url"),
            "country": article.get("sourcecountry"),
            "region": None,
            "topic": "geopolitics",
            "event_type": None,
            "severity_score": None,
            "confidence_score": 68,
            "published_at": None,
            "raw_ref": article.get("url")
        })

    if not rows:
        return {"inserted": 0, "data": []}

    result = supabase.table("normalized_signals").insert(rows).execute()
    return {
        "inserted": len(rows),
        "data": result.data
    }
