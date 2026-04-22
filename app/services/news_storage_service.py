from app.services.supabase_service import supabase

def save_raw_news(articles):
    rows = []
    for article in articles:
        rows.append({
            "source_name": article.get("source", {}).get("name"),
            "author": article.get("author"),
            "title": article.get("title"),
            "description": article.get("description"),
            "url": article.get("url"),
            "url_to_image": article.get("urlToImage"),
            "published_at": article.get("publishedAt"),
            "content": article.get("content")
        })

    if not rows:
        return {"inserted": 0, "data": []}

    result = supabase.table("raw_news").insert(rows).execute()
    return {
        "inserted": len(rows),
        "data": result.data
    }
