cat > app/api/ingest.py <<'PY'
from fastapi import APIRouter
from app.services.news_service import fetch_news
from app.services.news_storage_service import save_raw_news
from app.services.normalize_service import normalize_news_articles
from app.services.gdelt_service import fetch_gdelt
from app.services.gdelt_storage_service import save_raw_gdelt
from app.services.gdelt_normalize_service import normalize_gdelt_articles

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/test")
def test_ingest():
    return {"status": "ingest working"}


@router.get("/news")
def ingest_news(query: str = "geopolitics"):
    data = fetch_news(query=query)
    articles = data.get("articles", [])

    return {
        "source": "news",
        "count": len(articles),
        "sample": articles[:2],
        "error": data.get("message") if not articles else None
    }


@router.get("/news/save")
def ingest_and_save_news(query: str = "geopolitics"):
    data = fetch_news(query=query)
    articles = data.get("articles", [])

    if not articles:
        return {
            "source": "news",
            "fetched": 0,
            "saved": 0,
            "error": data.get("message", "No articles returned")
        }

    result = save_raw_news(articles)
    return {
        "source": "news",
        "fetched": len(articles),
        "saved": result.get("inserted", 0)
    }


@router.get("/news/normalize")
def ingest_and_normalize_news(query: str = "geopolitics"):
    data = fetch_news(query=query)
    articles = data.get("articles", [])

    if not articles:
        return {
            "source": "news",
            "fetched": 0,
            "normalized": 0,
            "error": data.get("message", "No articles returned")
        }

    result = normalize_news_articles(articles)
    return {
        "source": "news",
        "fetched": len(articles),
        "normalized": result.get("inserted", 0)
    }


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

    if not articles:
        return {
            "source": "gdelt",
            "fetched": 0,
            "saved": 0
        }

    result = save_raw_gdelt(articles)
    return {
        "source": "gdelt",
        "fetched": len(articles),
        "saved": result.get("inserted", 0)
    }


@router.get("/gdelt/normalize")
def ingest_and_normalize_gdelt(query: str = "geopolitics"):
    data = fetch_gdelt(query=query)
    articles = data.get("articles", []) if isinstance(data, dict) else []

    if not articles:
        return {
            "source": "gdelt",
            "fetched": 0,
            "normalized": 0
        }

    result = normalize_gdelt_articles(articles)
    return {
        "source": "gdelt",
        "fetched": len(articles),
        "normalized": result.get("inserted", 0)
    }
PY
