import feedparser
import re
from html import unescape
from datetime import datetime, timezone
from urllib.parse import quote_plus


def fetch_google_news_conflict_items(country: str, indicator: str | None = None, limit: int = 10):
    query_terms = f'{country} {indicator or "conflict escalation military security"}'
    encoded_query = quote_plus(query_terms)

    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)
    items = []

    for entry in feed.entries[:limit]:
        raw_summary = entry.get("summary", "")
        clean_summary = re.sub(r"<[^>]+>", "", raw_summary)
        clean_summary = unescape(clean_summary).strip()

        items.append({
            "title": entry.get("title", ""),
            "source": entry.get("source", {}).get("title", "Google News"),
            "url": entry.get("link", ""),
            "published": entry.get("published", ""),
            "snippet": clean_summary
        })

    return items


def score_live_rss_signals(items):
    text = " ".join([
        f"{item.get('title', '')} {item.get('summary', '')}".lower()
        for item in items
    ])

    return {
        "armed_clashes": sum(word in text for word in ["clash", "attack", "strike", "shelling", "fighting"]),
        "civil_unrest": sum(word in text for word in ["protest", "riot", "unrest", "demonstration"]),
        "terrorism_activity": sum(word in text for word in ["terror", "militant", "isis", "al qaeda", "bombing"]),
        "sanctions_pressure": any(word in text for word in ["sanction", "blacklist", "export control"]),
        "refugee_flows": 50000 if any(word in text for word in ["refugee", "displaced", "evacuation"]) else 0,
        "cyber_operations": sum(word in text for word in ["cyber", "hack", "malware", "espionage"]),
        "military_pressure": sum(word in text for word in ["military", "troops", "missile", "warship", "drill", "exercise"]),
        "border_incidents": sum(word in text for word in ["border", "incursion", "airspace", "median line"]),
        "maritime_incidents": sum(word in text for word in ["maritime", "naval", "ship", "vessel", "strait", "sea"])
    }


def fetch_conflict_signals(country: str, indicator: str | None = None, limit: int = 10):
    baseline_profiles = {
        "taiwan": {
            "armed_clashes": 2,
            "civil_unrest": 3,
            "terrorism_activity": 0,
            "sanctions_pressure": True,
            "refugee_flows": 0,
            "cyber_operations": 8,
            "military_pressure": 9,
            "border_incidents": 7,
            "maritime_incidents": 8,
        },
        "ukraine": {
            "armed_clashes": 15,
            "civil_unrest": 5,
            "terrorism_activity": 2,
            "sanctions_pressure": True,
            "refugee_flows": 500000,
            "cyber_operations": 7,
            "military_pressure": 10,
            "border_incidents": 9,
            "maritime_incidents": 4,
        },
        "sudan": {
            "armed_clashes": 14,
            "civil_unrest": 9,
            "terrorism_activity": 3,
            "sanctions_pressure": True,
            "refugee_flows": 700000,
            "cyber_operations": 2,
            "military_pressure": 8,
            "border_incidents": 6,
            "maritime_incidents": 1,
        },
    }

    default_profile = {
        "armed_clashes": 4,
        "civil_unrest": 5,
        "terrorism_activity": 1,
        "sanctions_pressure": False,
        "refugee_flows": 10000,
        "cyber_operations": 2,
        "military_pressure": 4,
        "border_incidents": 3,
        "maritime_incidents": 2,
    }

    country_key = (country or "").strip().lower()
    baseline = baseline_profiles.get(country_key, default_profile).copy()

    rss_items = fetch_google_news_conflict_items(country, indicator, limit)
    live_signals = score_live_rss_signals(rss_items)

    merged = baseline.copy()

    for key, value in live_signals.items():
        if isinstance(value, bool):
            merged[key] = merged.get(key, False) or value
        else:
            merged[key] = max(merged.get(key, 0), value)

    return {
        "country": country,
        "indicator": indicator,
        "limit": limit,
        "source_mode": "hybrid_baseline_google_news_rss_v1",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "signals": merged,
        "live_signals": live_signals,
        "rss_items": rss_items,
        "source_notes": [
            "Baseline profile merged with Google News RSS conflict/security signals.",
            "Google RSS is used instead of GDELT to avoid previous rate-limit issues.",
            "Next upgrade: add source reliability scoring and duplicate filtering."
        ]
    }
