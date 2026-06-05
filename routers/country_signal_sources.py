from typing import List, Dict, Any
from urllib.parse import quote_plus
from datetime import datetime
import xml.etree.ElementTree as ET
import requests
import re


SIGNAL_KEYWORDS = {
    "military": ["military", "troops", "missile", "drone", "naval", "border", "attack", "strike"],
    "sanctions": ["sanctions", "blacklist", "export control", "embargo"],
    "diplomacy": ["talks", "summit", "agreement", "treaty", "diplomatic", "ceasefire"],
    "economic": ["inflation", "currency", "debt", "default", "markets", "gdp", "bank", "trade"],
    "energy": ["oil", "gas", "lng", "pipeline", "electricity", "energy", "fuel"],
    "social_stability": ["protest", "riot", "strike", "unrest", "demonstration", "refugee"],
    "cyber": ["cyber", "hack", "ransomware", "data breach", "malware"],
    "supply_chain": ["port", "shipping", "supply chain", "semiconductor", "exports", "imports", "shortage"],
}


def clean_html(raw: str) -> str:
    if not raw:
        return ""
    return re.sub(r"<.*?>", "", raw).replace("&nbsp;", " ").strip()


def classify_signal(text: str) -> str:
    lower = text.lower()
    for domain, keywords in SIGNAL_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return domain
    return "geopolitical"


def estimate_severity(text: str) -> str:
    lower = text.lower()
    if any(t in lower for t in ["war", "invasion", "missile strike", "attack", "explosion", "coup"]):
        return "critical"
    if any(t in lower for t in ["sanctions", "troops", "deployment", "clashes", "unrest", "crisis", "blockade"]):
        return "high"
    return "monitoring"


def fetch_google_news_signals(country_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    queries = [
        f"{country_name}",
        f"{country_name} security",
        f"{country_name} economy",
        f"{country_name} military",
        f"{country_name} sanctions",
    ]

    seen = set()
    signals = []

    headers = {
        "User-Agent": "Mozilla/5.0 SovereignIntelligenceAI/1.0"
    }

    for q in queries:
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception:
            continue

        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            published = item.findtext("pubDate")
            description = clean_html(item.findtext("description") or "")

            if not title or title in seen:
                continue

            seen.add(title)
            text = f"{title} {description}"

            signals.append({
                "title": title,
                "source": "Google News RSS",
                "url": link,
                "published_at": published,
                "signal_domain": classify_signal(text),
                "severity": estimate_severity(text),
                "summary": description[:500]
            })

            if len(signals) >= limit:
                return signals

    return signals


def fetch_country_signals(country_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    try:
        return fetch_google_news_signals(country_name, limit=limit)
    except Exception as e:
        return [{
            "title": "Signal collection failed",
            "source": "internal",
            "url": None,
            "published_at": datetime.utcnow().isoformat(),
            "signal_domain": "system",
            "severity": "monitoring",
            "summary": str(e)
        }]


def analyze_signal_convergence(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    domain_counts = {}
    severity_counts = {"critical": 0, "high": 0, "monitoring": 0}

    for signal in signals:
        domain = signal.get("signal_domain", "geopolitical")
        severity = signal.get("severity", "monitoring")

        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    convergence_score = min(
        100,
        (severity_counts.get("critical", 0) * 18)
        + (severity_counts.get("high", 0) * 10)
        + (len(domain_counts) * 8)
    )

    if convergence_score >= 75:
        convergence_level = "Severe"
    elif convergence_score >= 50:
        convergence_level = "High"
    elif convergence_score >= 25:
        convergence_level = "Moderate"
    else:
        convergence_level = "Low"

    return {
        "convergence_score": convergence_score,
        "convergence_level": convergence_level,
        "domain_counts": domain_counts,
        "severity_counts": severity_counts,
        "dominant_domains": sorted(domain_counts, key=domain_counts.get, reverse=True)[:3]
    }
