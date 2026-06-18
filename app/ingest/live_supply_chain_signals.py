import os
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

QUERIES = [
    "supply chain disruption shipping port closure",
    "Strait of Hormuz shipping disruption",
    "Taiwan Strait semiconductor supply chain",
    "Suez Canal shipping disruption",
    "Bab el-Mandeb Red Sea shipping",
    "Panama Canal drought shipping",
    "port strike container congestion",
    "LNG shipping disruption",
    "semiconductor export controls supply chain",
]

CHOKEPOINTS = [
    "Strait of Hormuz",
    "Taiwan Strait",
    "Suez Canal",
    "Bab el-Mandeb",
    "Panama Canal",
    "Strait of Malacca",
]

PORTS = [
    "Port of Singapore",
    "Port of Shanghai",
    "Port of Rotterdam",
    "Jebel Ali Port",
    "Port of Los Angeles",
    "Port of Kaohsiung",
    "Port of Busan",
]

COMMODITIES = [
    "Crude Oil",
    "LNG",
    "Advanced Semiconductors",
    "Lithium",
    "Cobalt",
    "Copper",
    "Wheat",
    "Fertilizers",
]

COMPANIES = [
    "Apple",
    "Nvidia",
    "TSMC",
    "Samsung Electronics",
    "ExxonMobil",
    "Shell",
    "Maersk",
    "MSC",
    "Walmart",
]


def match_entity(text, values):
    text_lower = text.lower()
    for value in values:
        if value.lower() in text_lower:
            return value
    return None


def classify_event(text):
    t = text.lower()

    if any(x in t for x in ["closure", "closed", "blocked", "blockade"]):
        return "closure", 85
    if any(x in t for x in ["attack", "missile", "drone", "strike"]):
        return "security", 80
    if any(x in t for x in ["congestion", "delay", "queue", "backlog"]):
        return "congestion", 68
    if any(x in t for x in ["sanction", "export control", "restriction"]):
        return "regulatory", 72
    if any(x in t for x in ["drought", "storm", "typhoon", "weather"]):
        return "weather", 66

    return "monitoring", 55


def clean_text(value):
    if not value:
        return ""
    return re.sub("<[^<]+?>", "", value).strip()


def fetch_google_news(query):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    return feed.entries[:10]


def run_live_supply_chain_ingestion():
    rows = []

    for query in QUERIES:
        entries = fetch_google_news(query)

        for entry in entries:
            title = clean_text(entry.get("title"))
            summary = clean_text(entry.get("summary"))
            link = entry.get("link")
            published = entry.get("published")

            combined = f"{title} {summary}"

            event_type, severity = classify_event(combined)

            row = {
                "source": "google_news_rss",
                "title": title,
                "summary": summary,
                "url": link,
                "event_type": event_type,
                "matched_chokepoint": match_entity(combined, CHOKEPOINTS),
                "matched_port": match_entity(combined, PORTS),
                "matched_commodity": match_entity(combined, COMMODITIES),
                "matched_company": match_entity(combined, COMPANIES),
                "severity_score": severity,
                "confidence_score": 65,
                "published_at": None,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "raw_payload": dict(entry),
            }

            rows.append(row)

    if rows:
        supabase.table("sc_live_disruption_events").insert(rows[:100]).execute()

    print({
        "status": "success",
        "records_inserted": len(rows[:100])
    })


if __name__ == "__main__":
    run_live_supply_chain_ingestion()
