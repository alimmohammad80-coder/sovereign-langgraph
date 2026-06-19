import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
    "supply chain disruption port closure shipping",
    "Strait of Hormuz tanker LNG oil disruption",
    "Taiwan Strait semiconductor TSMC shipping disruption",
    "Suez Canal Red Sea shipping disruption",
    "Bab el-Mandeb Houthi Red Sea shipping",
    "Panama Canal drought shipping restrictions",
    "port strike container congestion shipping",
    "LNG shipping disruption QatarEnergy Shell",
    "semiconductor export controls TSMC Nvidia Apple",
    "critical minerals export controls lithium cobalt graphite rare earths",
]

ENTITY_ALIASES = {
    "Strait of Hormuz": ["hormuz", "strait of hormuz", "persian gulf"],
    "Taiwan Strait": ["taiwan strait", "taiwan blockade", "pla exercises", "tsmc"],
    "Suez Canal": ["suez", "suez canal"],
    "Bab el-Mandeb": ["bab el-mandeb", "red sea", "houthi"],
    "Panama Canal": ["panama canal", "panama drought"],
    "Strait of Malacca": ["malacca", "strait of malacca"],

    "Port of Singapore": ["port of singapore", "singapore port"],
    "Port of Shanghai": ["port of shanghai", "shanghai port"],
    "Port of Rotterdam": ["port of rotterdam", "rotterdam port"],
    "Jebel Ali Port": ["jebel ali", "jebel ali port"],
    "Port of Los Angeles": ["port of los angeles", "la port"],
    "Port of Kaohsiung": ["kaohsiung", "port of kaohsiung"],

    "Crude Oil": ["crude oil", "oil tanker", "oil exports", "petroleum"],
    "LNG": ["lng", "liquefied natural gas", "gas cargo"],
    "Advanced Semiconductors": ["semiconductor", "chip", "chips", "ai chip", "tsmc", "foundry"],
    "Lithium": ["lithium"],
    "Cobalt": ["cobalt"],
    "Copper": ["copper"],
    "Graphite": ["graphite"],
    "Rare Earth Elements": ["rare earth", "rare earths"],
    "Wheat": ["wheat"],
    "Fertilizers": ["fertilizer", "fertilizers"],

    "Apple": ["apple"],
    "Nvidia": ["nvidia", "nvda"],
    "TSMC": ["tsmc", "taiwan semiconductor"],
    "Samsung Electronics": ["samsung"],
    "ExxonMobil": ["exxon", "exxonmobil"],
    "Shell": ["shell"],
    "Maersk": ["maersk"],
    "MSC": ["msc"],
    "Walmart": ["walmart"],
    "QatarEnergy": ["qatarenergy"],
}

CHOKEPOINT_NAMES = {
    "Strait of Hormuz",
    "Taiwan Strait",
    "Suez Canal",
    "Bab el-Mandeb",
    "Panama Canal",
    "Strait of Malacca",
}

PORT_NAMES = {
    "Port of Singapore",
    "Port of Shanghai",
    "Port of Rotterdam",
    "Jebel Ali Port",
    "Port of Los Angeles",
    "Port of Kaohsiung",
}

COMMODITY_NAMES = {
    "Crude Oil",
    "LNG",
    "Advanced Semiconductors",
    "Lithium",
    "Cobalt",
    "Copper",
    "Graphite",
    "Rare Earth Elements",
    "Wheat",
    "Fertilizers",
}

COMPANY_NAMES = {
    "Apple",
    "Nvidia",
    "TSMC",
    "Samsung Electronics",
    "ExxonMobil",
    "Shell",
    "Maersk",
    "MSC",
    "Walmart",
    "QatarEnergy",
}


def clean_text(value):
    if not value:
        return ""
    value = re.sub("<[^<]+?>", "", value)
    value = value.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", value).strip()


def match_from_group(text, allowed_names):
    text_lower = text.lower()
    for canonical, aliases in ENTITY_ALIASES.items():
        if canonical not in allowed_names:
            continue
        for alias in aliases:
            if alias.lower() in text_lower:
                return canonical
    return None


def classify_event(text):
    t = text.lower()

    if any(x in t for x in ["closure", "closed", "blocked", "blockade", "suspended"]):
        return "closure", 86
    if any(x in t for x in ["attack", "missile", "drone", "strike", "houthi", "seized"]):
        return "security", 82
    if any(x in t for x in ["congestion", "delay", "queue", "backlog", "dwell"]):
        return "congestion", 68
    if any(x in t for x in ["sanction", "export control", "restriction", "curbs"]):
        return "regulatory", 74
    if any(x in t for x in ["drought", "storm", "typhoon", "weather", "draft restriction"]):
        return "weather", 68
    if any(x in t for x in ["shortage", "supply crunch", "supply risk"]):
        return "shortage", 70

    return "monitoring", 55


def parse_published(entry):
    published = entry.get("published")
    if not published:
        return None
    try:
        return parsedate_to_datetime(published).astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def fetch_google_news(query):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    return feed.entries[:8]


def run_live_supply_chain_ingestion():
    rows = []
    seen_urls = set()

    for query in QUERIES:
        for entry in fetch_google_news(query):
            title = clean_text(entry.get("title"))
            summary = clean_text(entry.get("summary"))
            link = entry.get("link")

            if not title or not link or link in seen_urls:
                continue

            seen_urls.add(link)
            combined = f"{title} {summary}"
            event_type, severity = classify_event(combined)

            row = {
                "source": "google_news_rss",
                "title": title,
                "summary": summary,
                "url": link,
                "event_type": event_type,
                "matched_chokepoint": match_from_group(combined, CHOKEPOINT_NAMES),
                "matched_port": match_from_group(combined, PORT_NAMES),
                "matched_commodity": match_from_group(combined, COMMODITY_NAMES),
                "matched_company": match_from_group(combined, COMPANY_NAMES),
                "severity_score": severity,
                "confidence_score": 70,
                "published_at": parse_published(entry),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "raw_payload": {
                    "source_title": (entry.get("source") or {}).get("title"),
                    "query": query,
                },
            }

            rows.append(row)

    inserted = 0
    for row in rows[:100]:
        try:
            supabase.table("sc_live_disruption_events").upsert(
                row,
                on_conflict="url"
            ).execute()
            inserted += 1
        except Exception as e:
            print({"failed": row.get("title"), "error": str(e)})

    result = {
        "status": "success",
        "records_upserted": inserted
    }
    print(result)
    return result


if __name__ == "__main__":
    run_live_supply_chain_ingestion()
