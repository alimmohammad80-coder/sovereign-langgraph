from app.services.supabase_service import supabase

def save_raw_gdelt(articles):
    rows = []
    for article in articles:
        rows.append({
            "title": article.get("title"),
            "url": article.get("url"),
            "source_country": article.get("sourcecountry"),
            "domain": article.get("domain"),
            "seendate": article.get("seendate"),
            "socialimage": article.get("socialimage"),
            "language": article.get("language")
        })

    if not rows:
        return {"inserted": 0, "data": []}

    result = supabase.table("raw_gdelt").insert(rows).execute()
    return {
        "inserted": len(rows),
        "data": result.data
    }
