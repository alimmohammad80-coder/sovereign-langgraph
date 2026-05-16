import os
from openai import OpenAI
from typing import List
from app.intelligence.schemas import IntelligenceSignal

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_intelligence_assessment(
    module: str,
    entity: str,
    indicator: str,
    score: int,
    level: str,
    signals: List[IntelligenceSignal],
) -> dict:
    signal_text = "\n".join(
        [
            f"- {s.title} | Source: {s.source} | Severity: {s.severity} | Summary: {s.summary}"
            for s in signals[:8]
        ]
    )

    prompt = f"""
You are Sovereign Intelligence's fusion analysis engine.

Generate a concise intelligence-grade assessment.

Module: {module}
Entity: {entity}
Indicator: {indicator}
Score: {score}
Level: {level}

Live Signals:
{signal_text}

Return JSON only with these keys:
executive_judgment
strategic_assessment
cross_domain_impacts
confidence
intelligence_gaps
recommended_actions
simulation_ready
simulation_triggers
related_entities

Keep it concise, serious, and operational.
Do not use markdown.
"""

    response = client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": "You are a senior geopolitical fusion intelligence analyst. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    import json

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "executive_judgment": response.choices[0].message.content,
            "strategic_assessment": "Fusion assessment generated, but JSON parsing failed.",
            "cross_domain_impacts": {},
            "confidence": "Moderate",
            "intelligence_gaps": ["Structured JSON parsing failed."],
            "recommended_actions": ["Review assessment manually."],
            "simulation_ready": score >= 55,
            "simulation_triggers": [indicator],
            "related_entities": [entity],
        }
