from fastapi import APIRouter
from app.services.supabase_service import supabase

router = APIRouter(
    prefix="/api/intelligence",
    tags=["News Cache"]
)

@router.get("/news-cache")
def news_cache(query: str = "Iran", limit: int = 10):

    result = (
        supabase
        .table("raw_gdelt")
        .select("*")
        .ilike("title", f"%{query}%")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "status": "success",
        "source": "supabase_cache",
        "query": query,
        "count": len(result.data),
        "articles": result.data
    }
