import os
import re
import httpx
import feedparser
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote_plus

from app.data.trusted_sources import (
    TRUSTED_SOURCES,
    TIER1_SOURCES,
    TIER2_SOURCES,
    BLOCKED_SOURCES,
    DOMAIN_KEYWORDS,
)

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")


def clean_source(source: str) -> str:
    return (source or "").lower().replace(".", "").strip()


def is_blocked_source(source: str) -> bool:
    s = clean_source(source)
    return any(b.replace(".", "") in s for b in BLOCKED_SOURCES)


def source_quality_score(source: str) -> int:
    s = clean_source(source)
    if any(t.replace(".", "") in s for t in TIER1_SOURCES):
        return 25
    if any(t.replace(".", "") in s for t in TIER2_SOURCES):
        return 15
    return 0


def is_trusted_source(source: str) -> bool:
    return (not is_blocked_source(source)) and source_quality_score(source) > 0


def is_relevant_article(article: Dict[str, Any], query: str) -> bool:
    text = f"{article.get('title','')} {article.get('summary','')}".lower()
    query_terms = [q.lower() for q in re.findall(r"[A-Za-z]{4,}", query)]
    hits = sum(1 for term in query_terms if term in text)
    return hits >= 2


def classify_domain(text: str) -> str:
    t = text.lower()
    scores = {
        domain: sum(1 for k in keywords if k in t)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "strategic"


def risk_score(text: str, domain: str) -> int:
    t = text.lower()
    score = 25

    high = ["attack", "strike", "blocked", "closed", "explosion", "missile", "war", "disruption", "sanction", "cyberattack"]
    medium = ["tension", "warning", "delay", "shortage", "risk", "threat", "pressure", "instability", "reroute", "drill", "exercise"]

    score += sum(12 for x in high if x in t)
    score += sum(6 for x in medium if x in t)

    escalation_terms = ["china", "taiwan", "pla", "strait", "naval", "semiconductor", "chips"]
    score += sum(5 for x in escalation_terms if x in t)

    if domain in ["chokepoint", "conflict", "energy"]:
        score += 15

    return min(score, 100)


def risk_level(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 50:
        return "Warning"
    if score >= 30:
        return "Watch"
    return "Low"


def extract_drivers(text: str) -> List[str]:
    t = text.lower()
    drivers = []

    mapping = {
        "shipping disruption": ["shipping", "tanker", "vessel", "port", "reroute"],
        "energy exposure": ["oil", "gas", "lng", "pipeline", "refinery"],
        "military escalation": ["military", "missile", "strike", "border", "mobilization", "drill", "exercise", "naval"],
        "sanctions pressure": ["sanction", "export control", "embargo"],
        "supply-chain stress": ["supply chain", "semiconductor", "chips", "rare earth", "critical minerals"],
        "cyber risk": ["cyber", "cyberattack", "hack"],
    }

    for driver, terms in mapping.items():
        if any(term in t for term in terms):
            drivers.append(driver)

    return drivers or ["strategic risk signal"]


async def fetch_newsapi(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    if not NEWSAPI_KEY:
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        
        "pageSize": min(limit, 100),
        "apiKey": NEWSAPI_KEY,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    articles = []
    for a in data.get("articles", []):
        source = (a.get("source") or {}).get("name") or ""
        articles.append({
            "title": a.get("title") or "",
            "summary": a.get("description") or "",
            "source": source,
            "url": a.get("url") or "",
            "published_at": a.get("publishedAt"),
            "provider": "NewsAPI",
        })
    return articles


async def fetch_google_rss(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    rss_query = f'{query} when:30d'
    rss_url = f"https://news.google.com/rss/search?q={quote_plus(rss_query)}&hl=en-US&gl=US&ceid=US:en"

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(rss_url)
        r.raise_for_status()

    feed = feedparser.parse(r.text)
    articles = []

    for entry in feed.entries[:limit]:
        raw_title = getattr(entry, "title", "")
        source = getattr(getattr(entry, "source", None), "title", "") or ""

        title = raw_title
        if " - " in raw_title:
            parts = raw_title.rsplit(" - ", 1)
            title = parts[0].strip()
            source = source or parts[1].strip()

        summary = re.sub("<.*?>", "", getattr(entry, "summary", "") or "")

        articles.append({
            "title": title,
            "summary": summary,
            "source": source,
            "url": getattr(entry, "link", ""),
            "published_at": getattr(entry, "published", None),
            "provider": "GoogleRSS",
        })

    return articles


def dedupe_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    clean = []

    for a in articles:
        key = (a.get("url") or a.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        clean.append(a)

    return clean


def article_to_signal(article: Dict[str, Any], forced_domain: str | None = None) -> Dict[str, Any]:
    text = f"{article.get('title','')} {article.get('summary','')}"
    domain = forced_domain or classify_domain(text)
    sq = source_quality_score(article.get("source", ""))
    score = min(100, risk_score(text, domain) + sq)

    return {
        "domain": domain,
        "title": article.get("title"),
        "summary": article.get("summary"),
        "source": article.get("source"),
        "source_quality": sq,
        "url": article.get("url"),
        "provider": article.get("provider"),
        "published_at": article.get("published_at"),
        "signal_score": score,
        "severity": risk_level(score),
        "confidence": min(90, 45 + score // 2),
        "drivers": extract_drivers(text),
        "created_at": datetime.utcnow().isoformat(),
    }


async def generate_news_signals(query: str, domains: List[str] | None = None, limit: int = 25) -> Dict[str, Any]:
    newsapi_articles = await fetch_newsapi(query, limit)
    rss_articles = await fetch_google_rss(query, limit)

    all_articles = dedupe_articles(newsapi_articles + rss_articles)

    accepted = []
    rejected_sources = []

    for a in all_articles:
        source = a.get("source", "")

        if is_blocked_source(source):
            rejected_sources.append(source)
            continue

        if is_trusted_source(source) or is_relevant_article(a, query):
            accepted.append(a)
        else:
            rejected_sources.append(source)

    forced_domain = domains[0] if domains and len(domains) == 1 else None
    signals = [article_to_signal(a, forced_domain=forced_domain) for a in accepted]

    if domains:
        signals = [s for s in signals if s["domain"] in domains]

    alerts = [s for s in signals if s["signal_score"] >= 60]

    return {
        "status": "success",
        "query": query,
        "articles_collected": len(all_articles),
        "trusted_articles": len(accepted),
        "sample_sources": list({a.get("source", "") for a in all_articles if a.get("source")})[:10],
        "rejected_sources": list({s for s in rejected_sources if s})[:10],
        "signals_created": len(signals),
        "alerts_triggered": len(alerts),
        "signals": signals[:limit],
        "alerts": alerts[:10],
    }
