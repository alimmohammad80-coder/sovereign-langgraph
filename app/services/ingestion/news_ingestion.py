import os
import hashlib
import uuid
import feedparser
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

try:
    from supabase import create_client
except Exception:
    create_client = None


GOOGLE_NEWS_TOPICS = [
    "Taiwan Strait military drills",
    "Strait of Hormuz shipping risk",
    "Red Sea shipping disruption",
    "South China Sea military activity",
    "Ukraine Russia escalation",
    "Iran Israel conflict",
    "semiconductor supply chain disruption",
    "cyber attack port infrastructure",
    "sanctions export controls China",
    "global energy supply disruption"
]


def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key or create_client is None:
        return None

    return create_client(url, key)


def make_id(title: str, url: str = "") -> str:
    """
    Generate deterministic UUID from title + URL so upsert works
    with Supabase UUID primary key.
    """
    raw = f"{title}|{url}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, raw))


def google_news_rss(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    q = query.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)
    items = []

    for entry in feed.entries[:limit]:
        title = entry.get("title", "")
        link = entry.get("link", "")
        published = entry.get("published", "")

        items.append({
            "id": make_id(title, link),
            "title": title,
            "summary": entry.get("summary", title),
            "source": "Google News RSS",
            "url": link,
            "score": 50,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "published_at": published,
            "domain": "geopolitical",
            "query": query
        })

    return items


def score_signal(title: str, summary: str = "") -> int:
    text = f"{title} {summary}".lower()
    score = 45

    critical_terms = [
        "attack", "missile", "blockade", "invasion", "war", "strike",
        "explosion", "closed", "shutdown", "seized", "sanctions"
    ]

    high_terms = [
        "military", "drills", "naval", "carrier", "shipping",
        "strait", "cyber", "oil", "gas", "semiconductor"
    ]

    if any(t in text for t in critical_terms):
        score += 25

    if any(t in text for t in high_terms):
        score += 15

    return min(score, 95)


def normalize_signal(item: Dict[str, Any]) -> Dict[str, Any]:
    score = score_signal(item.get("title", ""), item.get("summary", ""))

    return {
        "id": item["id"],
        "title": item.get("title", "Untitled Signal"),
        "summary": item.get("summary", ""),
        "source": item.get("source", "Google News RSS"),
        "url": item.get("url", ""),
        "score": score,
        "risk_score": score,
        "domain": item.get("domain", "geopolitical"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def save_signals(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    supabase = get_supabase()

    if not supabase:
        return {"saved": 0, "error": "Supabase not configured"}

    saved = 0
    skipped = 0
    errors = []

    for signal in signals:
        try:
            supabase.table("live_risk_signals").upsert(signal).execute()
            saved += 1
        except Exception as e:
            skipped += 1
            errors.append(str(e))

    return {
        "saved": saved,
        "skipped": skipped,
        "errors": errors[:5]
    }


def run_google_news_ingestion(limit_per_topic: int = 5) -> Dict[str, Any]:
    all_items = []

    for topic in GOOGLE_NEWS_TOPICS:
        try:
            all_items.extend(google_news_rss(topic, limit=limit_per_topic))
        except Exception as e:
            print(f"[ingestion] Google RSS failed for {topic}: {e}")

    normalized = [normalize_signal(i) for i in all_items]

    result = save_signals(normalized)

    return {
        "status": "success",
        "source": "google_news_rss",
        "topics": len(GOOGLE_NEWS_TOPICS),
        "signals_found": len(normalized),
        "storage": result
    }
