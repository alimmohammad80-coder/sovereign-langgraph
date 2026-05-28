from app.services.strategic_report_composer import select_trigger_event, validate_report
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import requests
from google import genai

import json
from app.services.strategic_report_composer import (
    select_trigger_event,
    build_strategic_early_warning_prompt,
    validate_report,
)

try:
    from supabase import create_client
except Exception as e:
    create_client = None
    print(f"[Early Warning] Supabase import unavailable: {e}")



GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_ANALYST_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"

router = APIRouter(
    prefix="/api/early-warning",
    tags=["Strategic Early Warning System"]
)


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if create_client and SUPABASE_URL and SUPABASE_KEY
    else None
)

if supabase:
    print("[Early Warning] Supabase configured.")
else:
    print("[Early Warning] Supabase not configured or unavailable.")


class WarningRequest(BaseModel):
    country: Optional[str] = None
    entity: Optional[str] = None
    region: Optional[str] = None
    topic: Optional[str] = None
    indicator: Optional[str] = None
    timeframe: Optional[str] = "30 days"
    include_scenarios: Optional[bool] = True


SECTOR_DEFINITIONS = [
    {
        "sector": "Geopolitical Escalation",
        "description": "Tracks interstate tension, diplomatic breakdown, military signaling, coercive pressure, and crisis escalation.",
        "keywords": [
            "war", "military", "border", "missile", "sanctions", "diplomatic",
            "embassy", "threat", "invasion", "mobilization", "naval", "airspace",
            "escalation", "deterrence", "crisis", "ultimatum"
        ],
        "relevant_modules": [
            "Global Strategic Risk Map",
            "Regional Intelligence Dashboard",
            "Run Geopolitical Agent",
            "Scenario Simulation Lab",
            "Strategic Early Warning System"
        ],
    },
    {
        "sector": "Security & Conflict",
        "description": "Tracks armed conflict, terrorism, coups, civil unrest, insurgency, border incidents, and internal instability.",
        "keywords": [
            "attack", "terror", "explosion", "coup", "insurgency", "riot",
            "protest", "clashes", "militia", "armed", "violence", "unrest",
            "security forces", "casualties", "bombing", "assassination"
        ],
        "relevant_modules": [
            "Run Security Analysis Agent",
            "Regional Intelligence Dashboard",
            "Global Strategic Risk Map",
            "Scenario Simulation Lab",
            "Strategic Early Warning System"
        ],
    },
    {
        "sector": "Energy & Commodity Risk",
        "description": "Tracks oil, gas, LNG, chokepoints, critical minerals, commodity shocks, and resource nationalism.",
        "keywords": [
            "oil", "gas", "lng", "energy", "pipeline", "tanker", "hormuz",
            "suez", "commodity", "rare earth", "mineral", "refinery",
            "opec", "price spike", "supply disruption", "crude", "shipping"
        ],
        "relevant_modules": [
            "Run Energy Analysis Agent",
            "Global Supply Chain Risk Engine",
            "Corporate Exposure & Portfolio Intelligence",
            "Scenario Simulation Lab",
            "Global Strategic Risk Map"
        ],
    },
    {
        "sector": "Supply Chain & Trade Disruption",
        "description": "Tracks maritime corridors, ports, sanctions, export controls, critical minerals, and logistics disruption.",
        "keywords": [
            "shipping", "port", "trade", "export control", "import", "supply chain",
            "logistics", "container", "maritime", "freight", "chokepoint",
            "red sea", "taiwan strait", "suez", "blockade", "tariff"
        ],
        "relevant_modules": [
            "Global Supply Chain Risk Engine",
            "Corporate Exposure & Portfolio Intelligence",
            "Scenario Simulation Lab",
            "Global Strategic Risk Map",
            "Run Geopolitical Agent"
        ],
    },
    {
        "sector": "Cyber & Information Operations",
        "description": "Tracks cyberattacks, disinformation, election interference, deepfakes, influence operations, and infrastructure targeting.",
        "keywords": [
            "cyber", "hack", "malware", "ransomware", "cve", "vulnerability",
            "disinformation", "deepfake", "propaganda", "influence operation",
            "information warfare", "critical infrastructure", "data breach"
        ],
        "relevant_modules": [
            "Cyber & Information Risk Layer",
            "Strategic Early Warning System",
            "Scenario Simulation Lab",
            "Corporate Exposure & Portfolio Intelligence"
        ],
    },
    {
        "sector": "Economic & Financial Stress",
        "description": "Tracks inflation, currency pressure, sovereign debt, sanctions exposure, capital flight, and market volatility.",
        "keywords": [
            "inflation", "currency", "debt", "default", "capital flight",
            "interest rate", "market", "banking", "financial crisis",
            "sanctions", "recession", "sovereign risk", "bond", "stocks"
        ],
        "relevant_modules": [
            "Corporate Exposure & Portfolio Intelligence",
            "Regional Intelligence Dashboard",
            "Scenario Simulation Lab",
            "Global Strategic Risk Map",
            "Strategic Early Warning System"
        ],
    },
    {
        "sector": "Political Stability & Governance",
        "description": "Tracks protests, election instability, elite fragmentation, legitimacy crisis, repression, and policy shocks.",
        "keywords": [
            "election", "protest", "government", "parliament", "president",
            "repression", "opposition", "legitimacy", "corruption", "policy shock",
            "state of emergency", "civil society", "regime", "cabinet"
        ],
        "relevant_modules": [
            "Run Geopolitical Agent",
            "Regional Intelligence Dashboard",
            "Scenario Simulation Lab",
            "Strategic Early Warning System"
        ],
    },
    {
        "sector": "Corporate & Portfolio Exposure",
        "description": "Tracks company exposure, asset exposure, operational risk, supply-chain dependencies, insurance risk, and investor impact.",
        "keywords": [
            "company", "corporate", "asset", "portfolio", "insurance", "operations",
            "factory", "investment", "market exposure", "supply dependency",
            "sanctions exposure", "business disruption", "earnings", "sector"
        ],
        "relevant_modules": [
            "Corporate Exposure & Portfolio Intelligence",
            "Global Supply Chain Risk Engine",
            "Scenario Simulation Lab",
            "Run Energy Analysis Agent",
            "Strategic Early Warning System"
        ],
    },
]


def classify_warning_level(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 50:
        return "Elevated"
    if score >= 30:
        return "Watch"
    return "Low"


def classify_signal_noise(score: int, has_system_notice: bool = False) -> Dict[str, str]:
    if has_system_notice:
        return {
            "classification": "Insufficient Live Data",
            "judgment": "Live external signal access is limited. The system is relying on structured analytical logic, known escalation pathways, and saved intelligence memory where available.",
            "meaning": "This should not be treated as absence of risk. It means the live feed requires corroboration from additional APIs, structured datasets, and analyst validation."
        }

    if score >= 85:
        return {
            "classification": "Strong Signal",
            "judgment": "The warning pattern is repeated, strategically meaningful, and consistent with known escalation pathways.",
            "meaning": "This is decision-relevant and should trigger senior review, automated alerting, and scenario/exposure analysis."
        }

    if score >= 70:
        return {
            "classification": "Signal",
            "judgment": "The warning appears relevant and actionable, with enough severity and momentum to justify escalation.",
            "meaning": "Users should monitor closely and consider running scenario, supply-chain, energy, or corporate exposure analysis."
        }

    if score >= 50:
        return {
            "classification": "Emerging Signal",
            "judgment": "The warning is not yet a crisis, but patterns are becoming relevant enough for active monitoring.",
            "meaning": "Users should track changes, compare with structured datasets, and build a warning timeline."
        }

    if score >= 30:
        return {
            "classification": "Mixed Signal",
            "judgment": "The warning contains some relevant indicators, but the evidence is partial, isolated, or not yet corroborated.",
            "meaning": "Users should avoid overreaction but continue monitoring for repetition, clustering, and escalation."
        }

    return {
        "classification": "Noise / Low Signal",
        "judgment": "Current signals are weak, isolated, or low-confidence.",
        "meaning": "No immediate action is required beyond routine monitoring."
    }


def calculate_warning_score(signals: List[Dict[str, Any]]) -> int:
    if not signals:
        return 35

    severity_total = 0
    probability_total = 0
    velocity_total = 0
    confidence_total = 0
    strategic_relevance_total = 0
    spillover_total = 0

    high_terms = [
        "attack", "strike", "missile", "war", "invasion", "sanctions",
        "mobilization", "military", "explosion", "terror", "cyberattack",
        "blockade", "coup", "riot", "crisis", "collapse", "nuclear",
        "escalation", "airstrike", "drone", "shipping attack", "oil disruption"
    ]

    medium_terms = [
        "tension", "warning", "dispute", "protest", "threat", "pressure",
        "border", "naval", "election", "instability", "shortage",
        "disruption", "militia", "embargo", "closure", "exercise"
    ]

    spillover_terms = [
        "oil", "gas", "shipping", "market", "supply chain", "cyber",
        "sanctions", "trade", "currency", "energy", "port", "commodity"
    ]

    for signal in signals:
        text = f"{signal.get('title', '')} {signal.get('summary', '')}".lower()

        severity = 20
        probability = 25
        velocity = 20
        confidence = 50
        strategic_relevance = 35
        spillover = 20

        if signal.get("source") == "system" or signal.get("category") == "system_notice":
            confidence = 25
            probability = 25
            strategic_relevance = 35

        for term in high_terms:
            if term in text:
                severity += 8
                probability += 5
                velocity += 5
                confidence += 3
                strategic_relevance += 4

        for term in medium_terms:
            if term in text:
                severity += 4
                probability += 3
                velocity += 3
                confidence += 2
                strategic_relevance += 2

        for term in spillover_terms:
            if term in text:
                spillover += 8
                strategic_relevance += 3

        severity_total += min(severity, 100)
        probability_total += min(probability, 100)
        velocity_total += min(velocity, 100)
        confidence_total += min(confidence, 95)
        strategic_relevance_total += min(strategic_relevance, 100)
        spillover_total += min(spillover, 100)

    n = len(signals)

    final_score = int(
        ((severity_total / n) * 0.25)
        + ((probability_total / n) * 0.20)
        + ((velocity_total / n) * 0.15)
        + ((confidence_total / n) * 0.15)
        + ((strategic_relevance_total / n) * 0.15)
        + ((spillover_total / n) * 0.10)
    )

    return max(0, min(final_score, 100))

def normalize_signal(
    title: str,
    summary: str = "",
    source: str = "unknown",
    domain: Optional[str] = None,
    url: Optional[str] = None,
    published_at: Optional[str] = None,
    category: str = "open_source_signal",
    signal_type: str = "news_signal",
) -> Dict[str, Any]:
    return {
        "title": title or "Untitled signal",
        "summary": summary or "",
        "source": source or "unknown",
        "domain": domain,
        "url": url,
        "published_at": published_at or datetime.utcnow().isoformat(),
        "category": category,
        "signal_type": signal_type,
    }


def fetch_gdelt_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": maxrecords,
            "sort": "hybridrel",
        }

        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])

        return [
            normalize_signal(
                title=article.get("title") or "Untitled GDELT signal",
                summary=article.get("seendate") or "",
                url=article.get("url"),
                source="GDELT",
                published_at=article.get("seendate"),
                domain=article.get("domain"),
                category="open_source_signal",
                signal_type="gdelt_news_signal",
            )
            for article in articles
        ]

    except Exception as e:
        print(f"[Early Warning] GDELT fetch error: {e}")
        return []


def fetch_newsapi_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    api_key = os.getenv("NEWS_API_KEY")

    if not api_key:
        return []

    try:
        url = "https://newsapi.org/v2/everything"

        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": maxrecords,
            "apiKey": api_key,
        }

        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])

        return [
            normalize_signal(
                title=article.get("title") or "Untitled NewsAPI signal",
                summary=article.get("description") or article.get("content") or "",
                source=article.get("source", {}).get("name") or "NewsAPI",
                domain=None,
                url=article.get("url"),
                published_at=article.get("publishedAt"),
                category="open_source_signal",
                signal_type="newsapi_signal",
            )
            for article in articles
        ]

    except Exception as e:
        print(f"[Early Warning] NewsAPI fetch error: {e}")
        return []


def fetch_reliefweb_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    try:
        url = "https://api.reliefweb.int/v1/reports"

        params = {
            "appname": "sovereign-intelligence",
            "query[value]": query,
            "limit": maxrecords,
            "sort[]": "date:desc",
            "profile": "list",
        }

        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        items = data.get("data", [])

        signals = []

        for item in items:
            fields = item.get("fields", {})

            signals.append(
                normalize_signal(
                    title=fields.get("title") or "Untitled ReliefWeb signal",
                    summary=fields.get("body") or "",
                    source="ReliefWeb",
                    domain="reliefweb.int",
                    url=fields.get("url"),
                    published_at=fields.get("date", {}).get("created"),
                    category="humanitarian_crisis_signal",
                    signal_type="reliefweb_report",
                )
            )

        return signals

    except Exception as e:
        print(f"[Early Warning] ReliefWeb fetch error: {e}")
        return []


def fetch_cisa_kev_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    try:
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

        response = requests.get(url, timeout=12)
        response.raise_for_status()
        data = response.json()

        vulnerabilities = data.get("vulnerabilities", [])

        query_terms = query.lower().split()

        matched = []

        for vuln in vulnerabilities[:200]:
            text = (
                f"{vuln.get('cveID', '')} "
                f"{vuln.get('vendorProject', '')} "
                f"{vuln.get('product', '')} "
                f"{vuln.get('vulnerabilityName', '')} "
                f"{vuln.get('shortDescription', '')}"
            ).lower()

            if any(term in text for term in query_terms) or "cyber" in query.lower():
                matched.append(
                    normalize_signal(
                        title=f"CISA KEV: {vuln.get('cveID', 'Unknown CVE')} — {vuln.get('vulnerabilityName', 'Known exploited vulnerability')}",
                        summary=vuln.get("shortDescription") or "",
                        source="CISA KEV",
                        domain="cisa.gov",
                        url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                        published_at=vuln.get("dateAdded"),
                        category="cyber_warning_signal",
                        signal_type="known_exploited_vulnerability",
                    )
                )

            if len(matched) >= maxrecords:
                break

        return matched

    except Exception as e:
        print(f"[Early Warning] CISA KEV fetch error: {e}")
        return []


def fetch_nvd_cve_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    try:
        if "cyber" not in query.lower() and "cve" not in query.lower() and "vulnerability" not in query.lower():
            return []

        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

        params = {
            "keywordSearch": query,
            "resultsPerPage": maxrecords,
        }

        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        items = data.get("vulnerabilities", [])

        signals = []

        for item in items:
            cve = item.get("cve", {})
            descriptions = cve.get("descriptions", [])
            description = ""

            for desc in descriptions:
                if desc.get("lang") == "en":
                    description = desc.get("value")
                    break

            signals.append(
                normalize_signal(
                    title=f"NVD CVE: {cve.get('id', 'Unknown CVE')}",
                    summary=description,
                    source="NVD",
                    domain="nist.gov",
                    url=f"https://nvd.nist.gov/vuln/detail/{cve.get('id')}" if cve.get("id") else None,
                    published_at=cve.get("published"),
                    category="cyber_warning_signal",
                    signal_type="cve_signal",
                )
            )

        return signals

    except Exception as e:
        print(f"[Early Warning] NVD CVE fetch error: {e}")
        return []


def fetch_google_news_rss_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    try:
        import feedparser
        from urllib.parse import quote_plus

        encoded_query = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

        feed = feedparser.parse(url)

        signals = []

        for entry in feed.entries[:maxrecords]:
            signals.append(
                normalize_signal(
                    title=entry.get("title") or "Untitled Google News RSS signal",
                    summary=entry.get("summary") or "",
                    source="Google News RSS",
                    domain="news.google.com",
                    url=entry.get("link"),
                    published_at=entry.get("published"),
                    category="open_source_signal",
                    signal_type="rss_news_signal",
                )
            )

        return signals

    except Exception as e:
        print(f"[Early Warning] Google News RSS fetch error: {e}")
        return []


def fetch_custom_rss_signals(query: str, maxrecords: int = 10) -> List[Dict[str, Any]]:
    try:
        import feedparser

        rss_feeds = [
            {
                "name": "BBC World",
                "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
                "domain": "bbc.co.uk",
            },
            {
                "name": "Al Jazeera",
                "url": "https://www.aljazeera.com/xml/rss/all.xml",
                "domain": "aljazeera.com",
            },
            {
                "name": "UN News",
                "url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
                "domain": "news.un.org",
            },
            {
                "name": "ReliefWeb Updates",
                "url": "https://reliefweb.int/updates/rss.xml",
                "domain": "reliefweb.int",
            },
            {
                "name": "CISA Alerts",
                "url": "https://www.cisa.gov/news-events/cybersecurity-advisories/all.xml",
                "domain": "cisa.gov",
            },
        ]

        query_terms = [
            term.lower()
            for term in query.split()
            if len(term) > 3
        ]

        signals = []

        for feed_info in rss_feeds:
            feed = feedparser.parse(feed_info["url"])

            for entry in feed.entries[:25]:
                title = entry.get("title") or ""
                summary = entry.get("summary") or ""
                text = f"{title} {summary}".lower()

                if any(term in text for term in query_terms):
                    signals.append(
                        normalize_signal(
                            title=title or "Untitled RSS signal",
                            summary=summary,
                            source=feed_info["name"],
                            domain=feed_info["domain"],
                            url=entry.get("link"),
                            published_at=entry.get("published"),
                            category="open_source_signal",
                            signal_type="rss_feed_signal",
                        )
                    )

                if len(signals) >= maxrecords:
                    return signals

        return signals

    except Exception as e:
        print(f"[Early Warning] Custom RSS fetch error: {e}")
        return []

def fetch_all_early_warning_signals(query: str, maxrecords: int = 12) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []

    source_plan = [
        ("Google News RSS", lambda: fetch_google_news_rss_signals(query, maxrecords=5)),
        ("Custom RSS", lambda: fetch_custom_rss_signals(query, maxrecords=5)),
        ("GDELT", lambda: fetch_gdelt_signals(query, maxrecords=4)),
    ]

    cyber_terms = [
        "cyber",
        "cve",
        "vulnerability",
        "ransomware",
        "malware",
        "hack",
        "critical infrastructure",
    ]

    if any(term in query.lower() for term in cyber_terms):
        source_plan.extend([
            ("CISA KEV", lambda: fetch_cisa_kev_signals(query, maxrecords=3)),
            ("NVD CVE", lambda: fetch_nvd_cve_signals(query, maxrecords=3)),
        ])

    if os.getenv("NEWS_API_KEY"):
        source_plan.append(
            ("NewsAPI", lambda: fetch_newsapi_signals(query, maxrecords=4))
        )

    for source_name, fetcher in source_plan:
        try:
            source_signals = fetcher()
            if source_signals:
                signals.extend(source_signals)
        except Exception as e:
            print(f"[Early Warning] {source_name} failed inside aggregator: {e}")

    deduped: List[Dict[str, Any]] = []
    seen = set()

    for signal in signals:
        title = str(signal.get("title") or "").strip().lower()
        url = str(signal.get("url") or "").strip()
        key = (title, url)

        if key not in seen:
            seen.add(key)
            deduped.append(signal)

    if not deduped:
        deduped.append(
            normalize_signal(
                title="Live external signal feed temporarily limited",
                summary=(
                    "No external source returned usable signals for this query. "
                    "The system is continuing with structured early-warning analysis, "
                    "sector logic, and saved intelligence memory where available."
                ),
                source="system",
                domain=None,
                url=None,
                published_at=datetime.utcnow().isoformat(),
                category="system_notice",
                signal_type="system_notice",
            )
        )

    return deduped[:maxrecords]



def build_warning_layers(score: int) -> List[Dict[str, Any]]:
    return [
        {
            "name": "Geopolitical Warning",
            "score": score,
            "status": classify_warning_level(score),
            "explanation": "Measures political, diplomatic, military, and interstate escalation pressure.",
        },
        {
            "name": "Security Instability",
            "score": max(20, score - 5),
            "status": classify_warning_level(max(20, score - 5)),
            "explanation": "Measures conflict, terrorism, unrest, protest, military activity, and internal security risk.",
        },
        {
            "name": "Economic Exposure",
            "score": max(15, score - 12),
            "status": classify_warning_level(max(15, score - 12)),
            "explanation": "Measures sanctions, market disruption, investor exposure, inflation pressure, and fiscal stress.",
        },
        {
            "name": "Energy/Supply Chain Spillover",
            "score": max(10, score - 8),
            "status": classify_warning_level(max(10, score - 8)),
            "explanation": "Measures chokepoint risk, shipping disruption, energy flows, commodity exposure, and trade disruption.",
        },
        {
            "name": "Cyber/Information Risk",
            "score": max(10, score - 15),
            "status": classify_warning_level(max(10, score - 15)),
            "explanation": "Measures cyber escalation, disinformation, information warfare, and digital infrastructure risk.",
        },
    ]



def score_sector_from_signals(
    sector: Dict[str, Any],
    signals: List[Dict[str, Any]],
    base_score: int
) -> int:
    text_blob = " ".join(
        [
            f"{signal.get('title', '')} {signal.get('summary', '')}".lower()
            for signal in signals
        ]
    )

    keyword_hits = 0

    for keyword in sector.get("keywords", []):
        if keyword.lower() in text_blob:
            keyword_hits += 1

    score = base_score

    if keyword_hits >= 6:
        score += 18
    elif keyword_hits >= 4:
        score += 12
    elif keyword_hits >= 2:
        score += 7
    elif keyword_hits >= 1:
        score += 4
    else:
        score -= 6

    return max(0, min(score, 100))



def build_current_assessment(
    country: str,
    topic: str,
    sector: str,
    score: int,
    status: str,
    has_system_notice: bool
) -> str:
    if has_system_notice:
        return (
            f"{sector} for {country} is under structured monitoring for {topic}, "
            f"but live external signals are currently limited. The system is maintaining a {status.lower()} posture "
            f"based on available indicators, known escalation pathways, RSS/API feeds, and analytical framework scoring."
        )

    return (
        f"{sector} for {country} is currently assessed at {status.lower()} warning posture "
        f"for {topic}. The assessment reflects sector relevance, signal language, potential spillover, "
        f"source diversity, and escalation sensitivity."
    )


def build_what_might_happen(sector: str, country: str, topic: str) -> List[str]:
    if sector == "Energy & Commodity Risk":
        return [
            "Oil, gas, LNG, or commodity price volatility may increase.",
            "Shipping insurance or transport costs may rise.",
            "Energy infrastructure or maritime chokepoints may become more exposed.",
            "Corporate and sovereign energy exposure may require reassessment."
        ]

    if sector == "Supply Chain & Trade Disruption":
        return [
            "Trade routes, ports, or maritime corridors may face disruption.",
            "Export controls or sanctions may affect exposed sectors.",
            "Logistics delays may create second-order effects for companies and investors.",
            "Critical mineral or semiconductor dependencies may become more visible."
        ]

    if sector == "Cyber & Information Operations":
        return [
            "Cyber activity may target public institutions, firms, or critical infrastructure.",
            "Disinformation or deepfake activity may increase around the crisis.",
            "Attribution ambiguity may complicate response options.",
            "Information operations may distort public perception and investor confidence."
        ]

    if sector == "Economic & Financial Stress":
        return [
            "Currency, inflation, or debt pressures may intensify.",
            "Sanctions or market volatility may affect capital flows.",
            "Investor exposure may require reassessment.",
            "Financial stress may spill into political or social instability."
        ]

    if sector == "Security & Conflict":
        return [
            "Localized incidents may become repeated or clustered.",
            "Security forces, militias, or armed actors may escalate activity.",
            "Civil unrest or violence may spread geographically.",
            "A triggering incident may change the warning level quickly."
        ]

    if sector == "Political Stability & Governance":
        return [
            "Protests, elite fragmentation, or legitimacy challenges may intensify.",
            "Election or governance disputes may create instability.",
            "Government repression or emergency measures may increase.",
            "Policy shocks may affect companies, markets, or diplomatic posture."
        ]

    if sector == "Corporate & Portfolio Exposure":
        return [
            "Exposed firms, assets, supply chains, or investments may face operational risk.",
            "Insurance, compliance, and sanctions exposure may increase.",
            "Portfolio sensitivity to the country or sector may rise.",
            "Decision-makers may need scenario and exposure analysis."
        ]

    return [
        "Diplomatic pressure, military signaling, or coercive behavior may intensify.",
        "Regional actors may adjust posture in response to perceived escalation.",
        "A trigger event may rapidly increase strategic risk.",
        "Cross-domain spillover may affect energy, markets, cyber, or supply chains."
    ]


def build_sector_monitoring_indicators(
    sector: str,
    country: str,
    topic: str
) -> List[Dict[str, str]]:
    common = [
        {
            "indicator": f"Increase in reporting volume related to {topic} in {country}",
            "relevance": "Medium",
            "status": "Monitoring",
            "escalation_threshold": "Escalate if reporting volume rises across multiple independent sources."
        },
        {
            "indicator": "Shift from rhetoric to operational activity",
            "relevance": "High",
            "status": "Monitoring",
            "escalation_threshold": "Escalate if statements are followed by military, cyber, economic, or coercive actions."
        },
    ]

    sector_specific = {
        "Geopolitical Escalation": [
            {
                "indicator": "Diplomatic breakdown, military signaling, sanctions, or coercive posture shift",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if rhetoric is followed by formal government action or observable movement."
            }
        ],
        "Security & Conflict": [
            {
                "indicator": "Repeated armed incidents, attacks, troop movement, or protest violence",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if incidents cluster geographically or involve state/security actors."
            }
        ],
        "Energy & Commodity Risk": [
            {
                "indicator": "Oil, gas, LNG, or commodity price movement linked to the crisis",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if price movement coincides with confirmed disruption or threat reporting."
            },
            {
                "indicator": "Chokepoint, tanker, pipeline, or port disruption",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Immediate escalation if confirmed by multiple sources."
            },
        ],
        "Supply Chain & Trade Disruption": [
            {
                "indicator": "Shipping delays, port closures, insurance premium changes, or rerouting",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if disruption affects major trade corridors or critical goods."
            }
        ],
        "Cyber & Information Operations": [
            {
                "indicator": "Cyber incident, disinformation campaign, deepfake, or infrastructure targeting",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if incident affects critical infrastructure, elections, markets, or public trust."
            }
        ],
        "Economic & Financial Stress": [
            {
                "indicator": "Currency pressure, inflation, sanctions, market volatility, or debt stress",
                "relevance": "Medium",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if financial stress aligns with political or security indicators."
            }
        ],
        "Political Stability & Governance": [
            {
                "indicator": "Protests, elite splits, election disputes, repression, or emergency rule",
                "relevance": "Medium",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if unrest spreads geographically or state response intensifies."
            }
        ],
        "Corporate & Portfolio Exposure": [
            {
                "indicator": "Operational disruption, asset exposure, insurance risk, sanctions exposure, or supply dependency",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if corporate assets, counterparties, or supply routes are directly affected."
            }
        ],
    }

    return common + sector_specific.get(sector, [])


def build_sector_recommended_actions(sector: str) -> List[str]:
    actions = [
        "Continue live signal tracking.",
        "Corroborate against structured datasets, RSS/API sources, and saved intelligence memory.",
        "Escalate if warning score rises above 70.",
    ]

    if sector == "Energy & Commodity Risk":
        actions += [
            "Run Energy Analysis Agent.",
            "Run Supply Chain Risk Engine.",
            "Generate Corporate Exposure Report for energy-sensitive assets."
        ]
    elif sector == "Supply Chain & Trade Disruption":
        actions += [
            "Run Global Supply Chain Risk Engine.",
            "Check chokepoint, port, sanctions, and commodity dependencies.",
            "Run Scenario Simulation Lab for disruption pathways."
        ]
    elif sector == "Cyber & Information Operations":
        actions += [
            "Monitor cyber advisories, CISA KEV, NVD CVE, and vulnerability feeds.",
            "Assess information manipulation and disinformation risk.",
            "Run scenario analysis for cyber-enabled escalation."
        ]
    elif sector == "Corporate & Portfolio Exposure":
        actions += [
            "Run Corporate Exposure & Portfolio Intelligence.",
            "Assess affected sectors, assets, counterparties, insurance, and sanctions exposure.",
            "Generate executive exposure brief."
        ]
    else:
        actions += [
            "Run Geopolitical or Security Analysis Agent.",
            "Run Scenario Simulation Lab.",
            "Update Global Strategic Risk Map layer."
        ]

    return actions


def build_sector_alerts(
    country: str,
    topic: str,
    overall_score: int,
    signals: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    has_system_notice = any(
        signal.get("source") == "system" or signal.get("category") == "system_notice"
        for signal in signals
    )

    sector_alerts = []

    topic_lower = topic.lower()

    for sector in SECTOR_DEFINITIONS:
        sector_score = score_sector_from_signals(sector, signals, overall_score)

        for keyword in sector["keywords"]:
            if keyword.lower() in topic_lower:
                sector_score = min(sector_score + 12, 100)
                break

        sector_status = classify_warning_level(sector_score)
        signal_noise = classify_signal_noise(sector_score, has_system_notice)

        sector_alerts.append(
            {
                "sector": sector["sector"],
                "description": sector["description"],
                "score": sector_score,
                "status": sector_status,
                "signal_or_noise": signal_noise["classification"],
                "signal_noise_judgment": signal_noise["judgment"],
                "signal_noise_meaning": signal_noise["meaning"],
                "current_assessment": build_current_assessment(
                    country=country,
                    topic=topic,
                    sector=sector["sector"],
                    score=sector_score,
                    status=sector_status,
                    has_system_notice=has_system_notice,
                ),
                "what_might_happen": build_what_might_happen(sector["sector"], country, topic),
                "monitoring_indicators": build_sector_monitoring_indicators(sector["sector"], country, topic),
                "recommended_actions": build_sector_recommended_actions(sector["sector"]),
                "relevant_modules": sector["relevant_modules"],
            }
        )

    return sorted(sector_alerts, key=lambda x: x["score"], reverse=True)


def generate_indicators(country: str, topic: str, signals: List[Dict[str, Any]]) -> List[str]:
    indicators = [
        f"Increase in reporting volume related to {topic} in {country}",
        "Shift from routine political rhetoric to coercive or operational language",
        "Movement from isolated incidents toward repeated or clustered events",
        "Emergence of cross-domain indicators involving security, energy, cyber, or economic pressure",
        "Growing mismatch between official statements and observable behavior",
    ]

    if signals:
        indicators.append("Multiple open-source signals require corroboration against structured datasets")

    return indicators


def build_monitoring_indicators_by_category(country: str, topic: str) -> Dict[str, List[Dict[str, str]]]:
    return {
        "Military/Security": [
            {
                "indicator": "Troop movement, missile/drone activity, attacks, or border incidents",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if confirmed movement or attack is reported by multiple sources."
            }
        ],
        "Diplomatic/Political": [
            {
                "indicator": "Diplomatic breakdown, sanctions announcement, embassy warning, or emergency meeting",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if diplomatic signaling shifts from rhetoric to formal action."
            }
        ],
        "Economic/Market": [
            {
                "indicator": "Currency movement, inflation pressure, market volatility, sanctions exposure",
                "relevance": "Medium",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if market stress aligns with security or political indicators."
            }
        ],
        "Energy/Supply Chain": [
            {
                "indicator": "Port disruption, tanker incident, chokepoint risk, oil/gas price volatility",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if physical disruption or credible threat affects a major corridor."
            }
        ],
        "Cyber/Information": [
            {
                "indicator": "Cyberattack, vulnerability exploitation, disinformation, deepfake, influence operation",
                "relevance": "Medium",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if linked to critical infrastructure, election integrity, or state-backed activity."
            }
        ],
        "Social/Local Stability": [
            {
                "indicator": "Protests, riots, repression, elite fragmentation, civil unrest",
                "relevance": "Medium",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if unrest spreads across cities or involves security-force violence."
            }
        ],
    }


def build_recommended_decision_actions() -> Dict[str, List[str]]:
    return {
        "Monitor": [
            "Continue live signal tracking.",
            "Watch for repeated indicators rather than isolated claims.",
            "Compare current signals with historical patterns."
        ],
        "Corroborate": [
            "Validate against GDELT, ACLED, sanctions, energy, cyber, and market data.",
            "Check source reliability and cross-source repetition.",
            "Separate official reporting from social amplification."
        ],
        "Escalate": [
            "Escalate if warning score exceeds 70.",
            "Notify analyst or decision-maker if a trigger indicator is confirmed.",
            "Generate executive brief if cross-domain spillover is detected."
        ],
        "Simulate": [
            "Run Scenario Simulation Lab.",
            "Test baseline, deterioration, and strategic shock pathways.",
            "Estimate second-order effects across markets, supply chains, and security."
        ],
        "Assess Exposure": [
            "Run Corporate Exposure & Portfolio Intelligence.",
            "Run Supply Chain Risk Engine.",
            "Run Energy Analysis Agent if energy, chokepoint, or commodity exposure is present."
        ],
    }


def infer_relevant_modules_from_topic(topic: str, sector_alerts: List[Dict[str, Any]]) -> List[str]:
    topic_lower = topic.lower()
    modules = set()

    for alert in sector_alerts[:3]:
        for module in alert.get("relevant_modules", []):
            modules.add(module)

    if any(word in topic_lower for word in ["oil", "gas", "hormuz", "energy", "lng", "chokepoint", "shipping", "suez", "red sea"]):
        modules.update([
            "Run Energy Analysis Agent",
            "Global Supply Chain Risk Engine",
            "Corporate Exposure & Portfolio Intelligence",
            "Scenario Simulation Lab",
            "Global Strategic Risk Map"
        ])

    if any(word in topic_lower for word in ["cyber", "deepfake", "disinformation", "information", "ransomware", "malware"]):
        modules.update([
            "Cyber & Information Risk Layer",
            "Scenario Simulation Lab",
            "Corporate Exposure & Portfolio Intelligence",
            "Strategic Early Warning System"
        ])

    if any(word in topic_lower for word in ["protest", "election", "coup", "governance", "unrest"]):
        modules.update([
            "Run Geopolitical Agent",
            "Run Security Analysis Agent",
            "Regional Intelligence Dashboard",
            "Scenario Simulation Lab"
        ])

    return sorted(modules)


def generate_scenarios(country: str, warning_level: str, topic: str) -> List[Dict[str, Any]]:
    return [
        {
            "scenario": "Baseline Continuity",
            "description": f"{country} remains under observation with limited escalation, but signals continue to accumulate around {topic}.",
            "probability": "Medium",
            "impact": "Moderate",
            "strategic_implication": "Decision-makers should continue monitoring but avoid overreacting without corroborated indicators.",
            "affected_sectors": ["Geopolitical Escalation", "Political Stability & Governance"],
            "trigger_indicators": [
                "Repeated official warnings",
                "Increased reporting volume",
                "Diplomatic friction",
                "Localized incidents without wider escalation"
            ]
        },
        {
            "scenario": "Accelerated Deterioration",
            "description": f"Warning indicators intensify, creating a higher-risk environment for security, markets, diplomacy, or operations in {country}.",
            "probability": "Medium-Low" if warning_level in ["Low", "Watch"] else "Medium-High",
            "impact": "High",
            "strategic_implication": "Organizations should review exposure, contingency plans, dependencies, and escalation thresholds.",
            "affected_sectors": ["Security & Conflict", "Energy & Commodity Risk", "Supply Chain & Trade Disruption"],
            "trigger_indicators": [
                "Military movement",
                "Sanctions announcement",
                "Port or chokepoint disruption",
                "Cyber incident",
                "Mass protest or security-force response"
            ]
        },
        {
            "scenario": "Strategic Shock",
            "description": f"A triggering event produces rapid escalation, forcing government, corporate, or investor reassessment of exposure to {country}.",
            "probability": "Low" if warning_level in ["Low", "Watch"] else "Medium",
            "impact": "Severe",
            "strategic_implication": "Rapid decision support, executive notification, and crisis-response protocols may be required.",
            "affected_sectors": ["Corporate & Portfolio Exposure", "Economic & Financial Stress", "Cyber & Information Operations"],
            "trigger_indicators": [
                "Missile or drone attack",
                "Major cyberattack",
                "Confirmed blockade or port closure",
                "Market shock",
                "Diplomatic rupture"
            ]
        },
    ]


def save_early_warning_run(result: Dict[str, Any]) -> Optional[str]:
    if not supabase:
        return None

    try:
        run_payload = {
            "country": result.get("country"),
            "region": result.get("region"),
            "topic": result.get("topic"),
            "timeframe": result.get("timeframe"),
            "warning_score": result.get("warning_score"),
            "warning_level": result.get("warning_level"),
            "executive_judgment": result.get("executive_judgment"),
            "engine": result.get("engine"),
            "status": result.get("status"),
            "confidence_score": result.get("confidence_score", 60),
        }

        run_response = supabase.table("early_warning_runs").insert(run_payload).execute()

        if not run_response.data:
            print("[Early Warning] Supabase run insert returned no data.")
            return None

        run_id = run_response.data[0]["id"]

        for signal in result.get("key_signals", []):
            supabase.table("early_warning_signals").insert(
                {
                    "run_id": run_id,
                    "title": signal.get("title") or "Untitled signal",
                    "summary": signal.get("summary"),
                    "source": signal.get("source"),
                    "domain": signal.get("domain"),
                    "url": signal.get("url"),
                    "published_at": signal.get("published_at"),
                    "category": signal.get("category"),
                    "signal_type": signal.get("signal_type"),
                    "country": result.get("country"),
                    "region": result.get("region"),
                    "severity_score": signal.get("severity_score", 50),
                    "reliability_score": signal.get("reliability_score", 50),
                    "relevance_score": signal.get("relevance_score", 50),
                }
            ).execute()

        for layer in result.get("warning_layers", []):
            supabase.table("early_warning_layers").insert(
                {
                    "run_id": run_id,
                    "layer_name": layer.get("name"),
                    "layer_score": layer.get("score"),
                    "layer_status": layer.get("status"),
                    "explanation": layer.get("explanation"),
                }
            ).execute()

        for indicator in result.get("early_warning_indicators", []):
            supabase.table("early_warning_indicators").insert(
                {
                    "run_id": run_id,
                    "indicator": indicator,
                    "status": "Monitoring",
                    "relevance": "Medium",
                    "analyst_note": "Automatically generated indicator requiring analyst validation.",
                }
            ).execute()

        for scenario in result.get("scenarios", []):
            supabase.table("early_warning_scenarios").insert(
                {
                    "run_id": run_id,
                    "scenario_name": scenario.get("scenario"),
                    "description": scenario.get("description"),
                    "probability": scenario.get("probability"),
                    "impact": scenario.get("impact"),
                    "strategic_implication": scenario.get("strategic_implication"),
                }
            ).execute()

        supabase.table("warning_score_history").insert(
            {
                "area": result.get("country") or "Global",
                "country": result.get("country"),
                "region": result.get("region"),
                "topic": result.get("topic"),
                "warning_score": result.get("warning_score"),
                "warning_level": result.get("warning_level"),
                "source_run_id": run_id,
            }
        ).execute()

        return run_id

    except Exception as e:
        print(f"[Early Warning] Supabase save error: {e}")
        return None




def get_early_warning_graph_context(
    entity: str = None,
    indicator: str = None,
    sector: str = None,
    region: str = None
):
    """
    Pull relevant Global Strategic Knowledge Graph context for Strategic Early Warning.
    Safe helper: never crashes the Early Warning endpoint.
    """
    try:
        from routers.strategic_knowledge_graph import (
            fetch_entity_by_name,
            fetch_relationships_for_entity,
            get_connected_entities,
            build_risk_pathways,
            recommend_modules,
        )

        graph_inputs = [entity, indicator, sector, region]
        graph_context = []

        for item in graph_inputs:
            if not item:
                continue

            matched = fetch_entity_by_name(item)
            if not matched:
                continue

            relationships = fetch_relationships_for_entity(matched["id"])
            connected = get_connected_entities(relationships)
            pathways = build_risk_pathways(matched, connected)
            modules = recommend_modules(matched, connected)

            graph_context.append({
                "input": item,
                "matched_entity": matched,
                "connected_entities": connected[:10],
                "risk_pathways": pathways[:8],
                "recommended_modules": modules,
            })

        strategic_pathways = []
        for block in graph_context:
            strategic_pathways.extend(block.get("risk_pathways", []))

        strategic_pathways = sorted(
            strategic_pathways,
            key=lambda x: x.get("risk_score", 0),
            reverse=True
        )[:12]

        return {
            "status": "success",
            "graph_context_available": True,
            "entities_analyzed": len(graph_context),
            "graph_context": graph_context,
            "strategic_pathways": strategic_pathways,
        }

    except Exception as e:
        return {
            "status": "error",
            "graph_context_available": False,
            "error": str(e),
            "graph_context": [],
            "strategic_pathways": [],
        }


@router.get("/health")
def early_warning_health():
    return {
        "status": "online",
        "module": "Strategic Early Warning System",
        "version": "early-warning-system-v3-sector-framework",
        "supabase_configured": True if supabase else False,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/run")
def run_early_warning_agent(request: WarningRequest):
    country = getattr(request, "entity", None) or request.country or "Global"
    topic = getattr(request, "indicator", None) or request.topic or "geopolitical risk"
    entity = country
    indicator = topic

    query = f"{country} {topic} crisis warning security escalation"
    signals = fetch_all_early_warning_signals(query=query, maxrecords=12)

    # Sovereign hard relevance filter: keep only signals tied to selected country/topic.
    country_l = (country or "").lower()
    topic_l = (topic or "").lower()
    topic_terms = [t for t in topic_l.replace("/", " ").replace("-", " ").split() if len(t) > 2]

    def is_relevant_signal(s):
        blob = f"{s.get('title','')} {s.get('summary','')} {s.get('source','')} {s.get('domain','')}".lower()
        country_match = country_l in blob if country_l else True
        topic_match = any(term in blob for term in topic_terms) if topic_terms else True
        china_taiwan_match = country_l == "taiwan" and ("china" in blob or "pla" in blob or "strait" in blob or "taiwan" in blob)
        return country_match and (topic_match or china_taiwan_match)

    signals = [s for s in signals if is_relevant_signal(s)]

    score = calculate_warning_score(signals)
    warning_level = classify_warning_level(score)

    has_system_notice = any(
        signal.get("source") == "system" or signal.get("category") == "system_notice"
        for signal in signals
    )

    signal_noise_assessment = classify_signal_noise(
        score=score,
        has_system_notice=has_system_notice
    )

    indicators = generate_indicators(country, topic, signals)
    scenarios = generate_scenarios(country, warning_level, topic) if request.include_scenarios else []
    warning_layers = build_warning_layers(score)

    sector_alerts = build_sector_alerts(
        country=country,
        topic=topic,
        overall_score=score,
        signals=signals
    )

    monitoring_indicators_by_category = build_monitoring_indicators_by_category(
        country=country,
        topic=topic
    )

    recommended_decision_actions = build_recommended_decision_actions()

    relevant_modules = infer_relevant_modules_from_topic(
        topic=topic,
        sector_alerts=sector_alerts
    )

    try:
        graph_context = get_early_warning_graph_context(
            entity=country,
            indicator=topic,
            sector=locals().get("sector"),
            region=request.region,
        )
    except Exception as graph_error:
        graph_context = {
            "status": "error",
            "graph_context_available": False,
            "error": str(graph_error),
            "graph_context": [],
            "strategic_pathways": [],
        }


    trigger_event = select_trigger_event(signals, country=country, topic=topic)

    report_prompt = build_strategic_early_warning_prompt(
        entity=country,
        indicator=topic,
        risk_score=score,
        risk_level=warning_level,
        confidence="Medium",
        time_horizon="30 days",
        trigger_event=trigger_event,
        signals=signals[:8],
    )

    fallback_report = {
        "bluf": f"{trigger_event.get('date')} — {trigger_event.get('title')} is the latest relevant development shaping the {topic} warning picture for {country}. Current indicators suggest a {warning_level.lower()} warning posture, with available evidence requiring continued corroboration.",
        "current_situation": f"{country} is currently assessed at a {warning_level.lower()} warning level for {topic}, with a warning score of {score}/100 and confidence score of 60/100. Current reporting should be treated as early warning material requiring further validation.",
        "strategic_assessment": f"The strategic significance of {topic} in {country} lies in its connection to military signaling, political coercion, semiconductor exposure, supply chains, and regional deterrence dynamics.",
        "forecast_outlook": "Over the next 30 days, the most likely trajectory is continued monitoring with moderate probability of intensified pressure if military activity, official rhetoric, or reporting volume increases.",
        "operational_implications": f"Decision-makers should monitor whether {topic} affects semiconductor supply chains, maritime routes, cyber exposure, military posture, or investor confidence linked to {country}."
    }

    gemini_debug_error = None
    gemini_raw_preview = None

    try:
        if not GEMINI_API_KEY:
            raise RuntimeError("Missing GEMINI_API_KEY")

        client = genai.Client(api_key=GEMINI_API_KEY)

        gemini_response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=report_prompt,
            config={
                "temperature": 0.25,
                "top_p": 0.8,
                "max_output_tokens": 1800
            }
        )

        raw_report = (getattr(gemini_response, "text", "") or "").strip()
        gemini_raw_preview = raw_report[:500]

        raw_report = raw_report.replace("```json", "").replace("```", "").strip()

        if "{" in raw_report and "}" in raw_report:
            raw_report = raw_report[raw_report.find("{"): raw_report.rfind("}") + 1]

        parsed_report = json.loads(raw_report)

    except Exception as e:
        gemini_debug_error = str(e)
        print(f"[EARLY WARNING GEMINI ERROR] {e}")
        parsed_report = fallback_report

    report = validate_report(parsed_report)


    result = {
        "engine": "sovereign_strategic_early_warning_system",
        "strategic_knowledge_graph": graph_context,
        "status": "success",
        "country": country,
        "region": request.region,
        "topic": topic,
        "timeframe": request.timeframe,
        "timestamp": datetime.utcnow().isoformat(),
        "warning_score": score,
        "warning_level": warning_level,
        "confidence_score": 60 if not has_system_notice else 35,
        "trigger_event": trigger_event,
        "report": report,
        "executive_judgment": (
            f"{country} currently registers a {warning_level.lower()} strategic warning posture "
            f"for {topic}. The assessment considers severity, probability, velocity, confidence, "
            f"strategic relevance, and cross-domain spillover. This should be treated as an early-warning "
            f"product designed to distinguish signal from noise, not as a final intelligence assessment."
        ),
        "warning_layers": warning_layers,
        "signal_noise_assessment": signal_noise_assessment,
        "sector_alerts": sector_alerts,
        "monitoring_indicators_by_category": monitoring_indicators_by_category,
        "recommended_decision_actions": recommended_decision_actions,
        "relevant_modules": relevant_modules,
        "key_signals": signals,
        "early_warning_indicators": indicators,
        "drivers": [
            "Escalatory political or military language",
            "Open-source reporting density",
            "Potential cross-domain spillover",
            "Regional or market sensitivity",
            "Uncertainty around adversary intent and capability",
            "Sector relevance to Sovereign Intelligence modules",
        ],
        "intelligence_gaps": [
            "Need corroboration from structured conflict datasets such as ACLED or similar sources",
            "Need baseline comparison against historical incident frequency",
            "Need source reliability weighting",
            "Need geospatial event clustering",
            "Need energy, sanctions, cyber, and market data fusion",
            "Need human analyst validation for high-impact warnings",
        ],
        "scenarios": scenarios,
        "recommended_monitoring": [
            "Track changes in warning score over the next 24–72 hours",
            "Compare media signals with ACLED/GDELT event data",
            "Monitor sanctions, cyber, military, and energy indicators",
            "Escalate to analyst review if score rises above 70",
            "Generate country-specific exposure report for affected assets or portfolios",
        ],
    }

    try:
        run_id = save_early_warning_run(result)
        result["supabase_run_id"] = run_id
        result["saved_to_supabase"] = True if run_id else False
    except Exception as e:
        result["supabase_run_id"] = None
        result["saved_to_supabase"] = False
        result["supabase_error"] = str(e)

    return result

@router.get("/dashboard")
def early_warning_dashboard(
    country: str = Query("Global"),
    topic: str = Query("geopolitical risk"),
):
    query = f"{country} {topic} warning crisis escalation"
    signals = fetch_all_early_warning_signals(query=query, maxrecords=8)
    score = calculate_warning_score(signals)
    level = classify_warning_level(score)
    warning_layers = build_warning_layers(score)

    has_system_notice = any(
        signal.get("source") == "system" or signal.get("category") == "system_notice"
        for signal in signals
    )

    signal_noise_assessment = classify_signal_noise(score, has_system_notice)

    sector_alerts = build_sector_alerts(
        country=country,
        topic=topic,
        overall_score=score,
        signals=signals
    )

    return {
        "module": "Strategic Early Warning Dashboard",
        "country": country,
        "topic": topic,
        "warning_score": score,
        "warning_level": level,
        "signal_noise_assessment": signal_noise_assessment,
        "summary": {
            "active_signals": len(signals),
            "priority": level,
            "watch_status": "Active Watch" if score >= 50 else "Routine Monitoring",
            "most_affected_sector": sector_alerts[0]["sector"] if sector_alerts else None,
            "recommended_posture": "Escalate / Active Review" if score >= 70 else "Active Monitoring" if score >= 40 else "Routine Monitoring",
            "last_updated": datetime.utcnow().isoformat(),
        },
        "warning_layers": warning_layers,
        "sector_alerts": sector_alerts,
        "signals": signals,
    }

@router.get("/global-watchlist")
def global_watchlist():
    monitored_areas = [
        {
            "area": "Taiwan Strait",
            "country": "China/Taiwan",
            "region": "Indo-Pacific",
            "topic": "Taiwan Strait escalation risk",
            "warning_score": 58,
            "warning_level": "Elevated",
            "most_affected_sector": "Geopolitical Escalation",
        },
        {
            "area": "Strait of Hormuz",
            "country": "Iran",
            "region": "Middle East",
            "topic": "Energy chokepoint and military escalation risk",
            "warning_score": 56,
            "warning_level": "Elevated",
            "most_affected_sector": "Energy & Commodity Risk",
        },
        {
            "area": "Red Sea Shipping Corridor",
            "country": "Yemen/Red Sea",
            "region": "Middle East / Africa",
            "topic": "Shipping disruption and maritime security risk",
            "warning_score": 54,
            "warning_level": "Elevated",
            "most_affected_sector": "Supply Chain & Trade Disruption",
        },
        {
            "area": "Russia-Ukraine War Zone",
            "country": "Ukraine",
            "region": "Europe",
            "topic": "Military escalation and European security risk",
            "warning_score": 68,
            "warning_level": "Elevated",
            "most_affected_sector": "Security & Conflict",
        },
        {
            "area": "India-Pakistan Crisis Corridor",
            "country": "India/Pakistan",
            "region": "South Asia",
            "topic": "Border escalation and nuclear signaling risk",
            "warning_score": 49,
            "warning_level": "Watch",
            "most_affected_sector": "Geopolitical Escalation",
        },
        {
            "area": "Korean Peninsula",
            "country": "North Korea/South Korea",
            "region": "East Asia",
            "topic": "Missile nuclear and military escalation risk",
            "warning_score": 61,
            "warning_level": "Elevated",
            "most_affected_sector": "Security & Conflict",
        },
        {
            "area": "Venezuela Political Crisis",
            "country": "Venezuela",
            "region": "Latin America",
            "topic": "Political instability and regional spillover risk",
            "warning_score": 44,
            "warning_level": "Watch",
            "most_affected_sector": "Political Stability & Governance",
        },
    ]

    watchlist = []

    for item in monitored_areas:
        watchlist.append({
            **item,
            "active_signals": 0,
            "strategic_relevance": (
                f"{item['area']} is relevant to Sovereign Intelligence because it can affect "
                f"security, markets, energy, supply chains, corporate exposure, or regional stability."
            ),
            "summary": (
                f"{item['area']} is under structured monitoring for escalation, instability, "
                f"strategic disruption, and cross-domain spillover."
            ),
        })

    return {
        "module": "Global Strategic Watchlist",
        "mode": "lightweight_structured_watchlist",
        "timestamp": datetime.utcnow().isoformat(),
        "watchlist": sorted(watchlist, key=lambda x: x["warning_score"], reverse=True),
    }

@router.get("/recent-runs")
def get_recent_early_warning_runs(limit: int = Query(10, ge=1, le=50)):
    if not supabase:
        return {
            "status": "unavailable",
            "message": "Supabase is not configured.",
            "runs": [],
        }

    try:
        response = (
            supabase.table("early_warning_runs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return {
            "status": "success",
            "runs": response.data or [],
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "runs": [],
        }


@router.get("/score-history")
def get_warning_score_history(
    area: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    if not supabase:
        return {
            "status": "unavailable",
            "message": "Supabase is not configured.",
            "history": [],
        }

    try:
        query = (
            supabase.table("warning_score_history")
            .select("*")
            .order("recorded_at", desc=True)
            .limit(limit)
        )

        if area:
            query = query.eq("area", area)

        response = query.execute()

        return {
            "status": "success",
            "area": area,
            "history": response.data or [],
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "history": [],
        }

from app.services.supabase_service import supabase


@router.get("/from-signals")
def early_warning_from_signals(country: str = "China", limit: int = 10):
    result = (
        supabase
        .table("risk_signals")
        .select("*")
        .eq("status", "new")
        .limit(limit)
        .execute()
    )

    signals = result.data or []

    if not signals:
        return {
            "status": "error",
            "message": "No active risk signals found"
        }

    scores = [int(s.get("severity") or 0) for s in signals]
    warning_score = int(sum(scores) / len(scores))

    warning_level = classify_warning_level(warning_score)

    simulation_triggers = []

    if warning_score >= 70:
        simulation_triggers.append(
            "Potential Taiwan Strait escalation pathway detected"
        )

    if warning_score >= 55:
        simulation_triggers.append(
            "Multi-domain geopolitical pressure indicators rising"
        )

    warning_layers = build_warning_layers(warning_score)

    return {
        "status": "success",
        "engine": "sovereign_strategic_early_warning_from_risk_signals",
        "country": country,
        "warning_score": warning_score,
        "warning_level": warning_level,
        "signal_count": len(signals),
        "warning_layers": warning_layers,
        "key_drivers": [
            {
                "title": s.get("title"),
                "severity": s.get("severity"),
                "risk_level": s.get("risk_level"),
                "source": s.get("source_provider"),
                "url": s.get("source_url")
            }
            for s in signals[:5]
        ],
        "recommended_actions": [
            "Maintain enhanced monitoring",
            "Review latest fusion intelligence report",
            "Track changes in warning score over the next 24–72 hours",
            "Escalate to simulation lab if warning level rises"
        ],
        "simulation_triggers": simulation_triggers,
        "simulation_ready": warning_score >= 55
    }



