import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from app.services.supabase_service import supabase

load_dotenv(".env")


# -----------------------------
# Config
# -----------------------------
DEFAULT_FETCH_LIMIT = 120
DEFAULT_OUTPUT_LIMIT = 10

# Expand this over time as you add more country pages.
KNOWN_COUNTRIES = {
    "afghanistan", "algeria", "argentina", "armenia", "australia", "austria",
    "azerbaijan", "bangladesh", "belarus", "belgium", "bolivia", "brazil",
    "bulgaria", "canada", "chile", "china", "colombia", "croatia", "cyprus",
    "czech republic", "denmark", "egypt", "estonia", "ethiopia", "finland",
    "france", "georgia", "germany", "ghana", "greece", "hungary", "india",
    "indonesia", "iran", "iraq", "ireland", "israel", "italy", "japan",
    "jordan", "kazakhstan", "kenya", "kuwait", "kyrgyzstan", "latvia",
    "lebanon", "libya", "lithuania", "malaysia", "mexico", "morocco",
    "netherlands", "new zealand", "nigeria", "norway", "oman", "pakistan",
    "palestine", "philippines", "poland", "portugal", "qatar", "romania",
    "russia", "saudi arabia", "serbia", "singapore", "somalia",
    "south africa", "south korea", "spain", "sri lanka", "sudan", "sweden",
    "switzerland", "syria", "tajikistan", "thailand", "tunisia", "turkey",
    "turkiye", "turkmenistan", "uae", "uk", "ukraine", "united arab emirates",
    "united kingdom", "united states", "usa", "uzbekistan", "venezuela",
    "yemen"
}

COUNTRY_ALIASES = {
    "us": "united states",
    "u.s.": "united states",
    "america": "united states",
    "britain": "united kingdom",
    "uk": "united kingdom",
    "uae": "united arab emirates",
    "turkiye": "turkey",
}


# -----------------------------
# Utilities
# -----------------------------
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing")
    return OpenAI(api_key=api_key)


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z\-\.\']+", normalize_text(text))


def normalize_query(query: Optional[str]) -> str:
    q = normalize_text(query)
    return COUNTRY_ALIASES.get(q, q)


def is_country_query(query: Optional[str]) -> bool:
    q = normalize_query(query)
    return q in KNOWN_COUNTRIES


def safe_json_load(text: str) -> Dict[str, Any]:
    text = text.strip()

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences if model adds them
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    return json.loads(text)


def dedupe_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Tuple[str, str, str]] = set()
    cleaned: List[Dict[str, Any]] = []

    for row in rows:
        key = (
            normalize_text(row.get("title")),
            normalize_text(row.get("country")),
            normalize_text(row.get("topic")),
        )
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(row)

    return cleaned


# -----------------------------
# Data fetch + ranking
# -----------------------------
def fetch_candidate_rows(limit: int = DEFAULT_FETCH_LIMIT) -> List[Dict[str, Any]]:
    result = (
        supabase.table("normalized_signals")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data if result.data else []


def score_row_for_query(row: Dict[str, Any], query: Optional[str]) -> int:
    if not query:
        return 1

    q = normalize_query(query)
    title = normalize_text(row.get("title"))
    summary = normalize_text(row.get("summary"))
    country = normalize_text(row.get("country"))
    region = normalize_text(row.get("region"))
    topic = normalize_text(row.get("topic"))

    combined = f"{title} {summary} {country} {region} {topic}"
    score = 0

    # Country-query mode: much stricter
    if is_country_query(q):
        if country == q:
            score += 20
        elif q in title:
            score += 8
        elif q in summary:
            score += 5
        elif q in region:
            score += 2

        # Penalize if query only weakly appears but another country seems primary
        if country and country != q and q not in title and q not in summary:
            score -= 5

    # General topic mode
    else:
        if q in title:
            score += 10
        if q in summary:
            score += 7
        if q in topic:
            score += 5
        if q in region:
            score += 3
        if q in country:
            score += 8

        # Token overlap bonus
        query_tokens = set(tokenize(q))
        row_tokens = set(tokenize(combined))
        overlap = len(query_tokens.intersection(row_tokens))
        score += overlap * 2

    return score


def get_recent_normalized_signals(limit: int = DEFAULT_FETCH_LIMIT, query: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = fetch_candidate_rows(limit=DEFAULT_FETCH_LIMIT)
    rows = dedupe_rows(rows)

    if not query or not query.strip():
        return rows[:limit]

    ranked: List[Tuple[int, Dict[str, Any]]] = []
    for row in rows:
        score = score_row_for_query(row, query)
        if score >= 4:
            ranked.append((score, row))

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1].get("created_at") or ""
        )
    )

    return [row for _, row in ranked[:limit]]


# -----------------------------
# LLM input shaping
# -----------------------------
def build_signal_input(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []

    for row in rows:
        cleaned.append({
            "id": row.get("id"),
            "title": row.get("title"),
            "summary": row.get("summary"),
            "country": row.get("country"),
            "region": row.get("region"),
            "topic": row.get("topic"),
            "confidence_score": row.get("confidence_score"),
            "updated_at": row.get("created_at"),
        })

    return cleaned


def build_prompt(payload: List[Dict[str, Any]], limit: int, query: Optional[str]) -> str:
    active_query = query if query else "general recent developments"
    strict_mode = is_country_query(query)

    return f"""
You are a senior intelligence analyst producing a premium strategic signals feed.

Objective:
Transform the input records into concise, high-relevance English intelligence signals.

Active query:
{active_query}

Rules:
- Translate any non-English content into natural English.
- Do not mention publishers, source names, domains, or URLs.
- Remove duplicates, event echo, and low-value noise.
- Focus on developments with geopolitical, security, energy, or economic significance.
- Be conservative and disciplined. Do not overstate uncertain claims.
- Return ONLY valid JSON.
- Return at most {limit} signals.

Relevance rules:
- Prioritize strict relevance to the active query.
- If a signal is only indirectly related, exclude it.
- {"This is a country query. Prefer signals where that country is the primary subject, not merely mentioned in passing." if strict_mode else "This is a topic query. Prefer signals where the topic is central, not incidental."}

Writing rules:
- title: short, sharp, English, intelligence-style
- summary: 2-3 sentences, direct and analytic
- why_it_matters: 1-2 sentences explaining strategic significance
- category: choose exactly one of:
  Geopolitics, Security, Energy, Economics
- confidence: integer from 0 to 100

Required JSON format:
{{
  "signals": [
    {{
      "title": "short English title",
      "summary": "2-3 sentence English summary",
      "why_it_matters": "1-2 sentence strategic relevance",
      "country": "country name or null",
      "region": "region name or null",
      "category": "Geopolitics or Security or Energy or Economics",
      "confidence": 0,
      "updated_at": "timestamp from input if available"
    }}
  ]
}}

Input records:
{json.dumps(payload, ensure_ascii=False)}
""".strip()


# -----------------------------
# Public entrypoint
# -----------------------------
def generate_curated_signals(limit: int = DEFAULT_OUTPUT_LIMIT, query: Optional[str] = None) -> Dict[str, Any]:
    client = get_openai_client()

    rows = get_recent_normalized_signals(limit=40, query=query)
    payload = build_signal_input(rows)

    # Graceful empty result
    if not payload:
        return {"signals": []}

    prompt = build_prompt(payload=payload, limit=limit, query=query)

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": "You convert noisy multilingual signal inputs into highly relevant English strategic intelligence summaries."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
    )

    content = response.choices[0].message.content or ""
    data = safe_json_load(content)

    # Safety normalization
    signals = data.get("signals", [])
    if not isinstance(signals, list):
        return {"signals": []}

    normalized_signals: List[Dict[str, Any]] = []
    for item in signals[:limit]:
        if not isinstance(item, dict):
            continue

        normalized_signals.append({
            "title": item.get("title"),
            "summary": item.get("summary"),
            "why_it_matters": item.get("why_it_matters"),
            "country": item.get("country"),
            "region": item.get("region"),
            "category": item.get("category"),
            "confidence": item.get("confidence"),
            "updated_at": item.get("updated_at"),
        })

    return {"signals": normalized_signals}

