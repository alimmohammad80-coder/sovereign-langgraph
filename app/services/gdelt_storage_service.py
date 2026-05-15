from app.services.supabase_service import supabase


def save_raw_gdelt(articles):

    rows = []

    for article in articles:

        rows.append({
            "title": article.get("title"),
            "title_en": article.get("title_en"),
            "url": article.get("url"),
            "source_country": article.get("source"),
            "domain": article.get("domain"),
            "seendate": article.get("seendate"),
            "summary": article.get("summary"),
            "summary_en": article.get("summary_en"),
            "image_url": (
                article.get("summary")
                if str(article.get("summary", "")).startswith("http")
                else None
            ),
            "language": article.get("language"),
            "relevance_score": article.get("relevance_score")
        })

    if not rows:
        return {
            "inserted": 0,
            "data": []
        }

    result = supabase.table("raw_gdelt").upsert(
        rows,
        on_conflict="url"
    ).execute()

    return {
        "inserted": len(rows),
        "data": result.data
    }
