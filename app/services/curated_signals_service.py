import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.supabase_service import supabase

load_dotenv(".env")

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing")
    return OpenAI(api_key=api_key)

def get_recent_normalized_signals(limit=30):
    result = (
        supabase.table("normalized_signals")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data if result.data else []

def build_signal_input(rows):
    cleaned = []
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

def generate_curated_signals(limit=10):
    client = get_openai_client()

    rows = get_recent_normalized_signals(limit=30)
    payload = build_signal_input(rows)

    prompt = f"""
You are an intelligence analyst.

Task:
Convert the input signals into concise English-language curated intelligence signals.

Rules:
- Translate any non-English content into natural English.
- Do not mention publishers, source names, domains, or URLs.
- Remove duplicates and low-value noise.
- Focus on meaningful geopolitical, security, economic, or energy developments.
- Write clearly and professionally.
- If the original text is vague, infer the likely strategic meaning conservatively.
- Return ONLY valid JSON.
- Return at most {limit} signals.

Required JSON format:
{{
  "signals": [
    {{
      "title": "short English title",
      "summary": "2-3 sentence English summary of what is happening",
      "why_it_matters": "1-2 sentence explanation of strategic relevance",
      "country": "country name or null",
      "region": "region name or null",
      "category": "Geopolitics or Security or Energy or Economics",
      "confidence": 0,
      "updated_at": "timestamp from input if available"
    }}
  ]
}}

Input signals:
{json.dumps(payload, ensure_ascii=False)}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "You convert raw multilingual signals into concise English intelligence summaries."
            },
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content
    return json.loads(content)
