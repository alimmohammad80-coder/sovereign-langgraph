import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def build_supply_chain_fusion_brief(
    country=None,
    sector=None,
    chokepoint=None,
    commodity=None,
    risk_score=None,
    risk_level=None,
    forecast=None,
    live_articles=None,
    extracted_signals=None,
    live_signals=None,
    sanctions_matches=None,
    cascading_effects=None,
    event_analysis=None,
):
    live_articles = live_articles or []
    extracted_signals = extracted_signals or []
    live_signals = live_signals or {}
    sanctions_matches = sanctions_matches or []
    cascading_effects = cascading_effects or []
    event_analysis = event_analysis or {}

    articles_text = "\n".join([
        f"- {a.get('title')} | {a.get('source')} | {a.get('published_at')} | {a.get('url')}"
        for a in live_articles[:8]
        if a.get("title")
    ])

    prompt = f"""
You are a senior supply-chain intelligence analyst for Sovereign Intelligence.

Write a concise but high-quality intelligence briefing based on live signals, news, sanctions, and supply-chain exposure.

Do not write generic dashboard text.
Do not overstate uncertainty.
Distinguish confirmed disruption from elevated risk.
Use analytical judgment.

INPUT:
Country: {country}
Sector: {sector}
Chokepoint: {chokepoint}
Commodity: {commodity}
Risk score: {risk_score}
Risk level: {risk_level}
Forecast: {forecast}

Live signals:
{live_signals}

Extracted signals:
{extracted_signals}

Sanctions matches:
{sanctions_matches[:5]}

Cascading effects:
{cascading_effects}

Event analysis:
{event_analysis}

Live articles:
{articles_text}

Return JSON only with these fields:
executive_judgment
current_situation
strategic_significance
exposure_assessment
market_implications
escalation_assessment
forecast_outlook
confidence_assessment
intelligence_gaps
decision_considerations
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You produce analyst-grade supply-chain intelligence briefings in strict JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.25
        )

        content = response.choices[0].message.content

        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw_text": content}

        return {
            "status": "success",
            "fusion_brief": parsed
        }

    except Exception as e:
        return {
            "status": "error",
            "fusion_brief": None,
            "error": str(e)
        }
