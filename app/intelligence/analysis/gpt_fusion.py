import os
import json
from openai import OpenAI


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    return OpenAI(api_key=api_key)


def generate_intelligence_assessment(
    module,
    entity,
    indicator,
    level,
    score,
    signals,
):
    client = get_openai_client()

    signal_text = "\n".join([
        f"- {s.title}: {s.summary}"
        for s in signals
    ])

    prompt = f"""
You are Sovereign Intelligence's fusion analysis engine.

Return VALID JSON only.

Entity: {entity}
Module: {module}
Indicator: {indicator}
Warning Level: {level}
Score: {score}

Signals:
{signal_text}

Return this exact JSON structure:
{{
  "executive_judgment": "short intelligence judgment",
  "strategic_assessment": "concise strategic assessment",
  "cross_domain_impacts": {{
    "military": "",
    "political": "",
    "economic": "",
    "cyber": "",
    "supply_chain": "",
    "financial": ""
  }},
  "confidence": "Low / Moderate / High",
  "intelligence_gaps": [],
  "recommended_actions": [],
  "simulation_ready": true,
  "simulation_triggers": [],
  "related_entities": []
}}

Do not use markdown.
Do not wrap JSON in code fences.
"""

    response = client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": "You are a senior strategic intelligence analyst. Return valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    text = response.choices[0].message.content

    try:
        return json.loads(text)
    except Exception:
        return {
            "executive_judgment": text,
            "strategic_assessment": "JSON parsing failed; raw model output returned in executive_judgment.",
            "cross_domain_impacts": {},
            "confidence": "Moderate",
            "intelligence_gaps": ["Model returned non-JSON output."],
            "recommended_actions": ["Review fusion prompt or retry assessment."],
            "simulation_ready": score >= 55,
            "simulation_triggers": [],
            "related_entities": []
        }
