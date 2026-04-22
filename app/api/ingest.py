from fastapi import APIRouter
from app.services.news_service import fetch_news
from app.services.news_storage_service import save_raw_news
from app.services.normalize_service import normalize_news_articles
from app.services.gdelt_service import fetch_gdelt
from app.services.gdelt_storage_service import save_raw_gdelt
from app.services.gdelt_normalize_service import normalize_gdelt_articles

router = APIRouter(prefix="/ingest", tags=["ingest"])

# -------------------
# TEST
# -------------------
@router.get("/test")
def test_ingest():
    return {"status": "ingest working"}

# -------------------
# NEWS
# -------------------
@router.get("/news")
def ingest_news(query: str = "geopolitics"):
    data = fetch_news(query=query)
    return {
        "source": "news",
        "count": len(data.get("articles", [])),
        "sample": data.get("articles", [])[:2]
    }

@router.get("/news/save")
def ingest_and_save_news(query: str = "geopolitics"):
    data = fetch_news(query=query)
    articles = data.get("articles", [])
    result = save_raw_news(articles)
    return {
        "source": "news",
        "fetched": len(articles),
        "saved": result["inserted"]
    }

@router.get("/news/normalize")
def ingest_and_normalize_news(query: str = "geopolitics"):
    data = fetch_news(query=query)
    articles = data.get("articles", [])
    result = normalize_news_articles(articles)
    return {
        "source": "news",
        "fetched": len(articles),
        "normalized": result["inserted"]
    }

# -------------------
# GDELT
# -------------------
@router.get("/gdelt")
def ingest_gdelt(query: str = "geopolitics"):
    data = fetch_gdelt(query=query)
    articles = data.get("articles", []) if isinstance(data, dict) else []
    return {
        "source": "gdelt",
        "count": len(articles),
        "sample": articles[:2]
    }

@router.get("/gdelt/save")
def ingest_and_save_gdelt(query: str = "geopolitics"):
    data = fetch_gdelt(query=query)
    articles = data.get("articles", []) if isinstance(data, dict) else []
    result = save_raw_gdelt(articles)
    return {
        "source": "gdelt",
        "fetched": len(articles),
        "saved": result["inserted"]
    }

@router.get("/gdelt/normalize")
def ingest_and_normalize_gdelt(query: str = "geopolitics"):
    data = fetch_gdelt(query=query)
    articles = data.get("articles", []) if isinstance(data, dict) else []
    result = normalize_gdelt_articles(articles)
    return {
        "source": "gdelt",
        "fetched": len(articles),
        "normalized": result["inserted"]
    }
