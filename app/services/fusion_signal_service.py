from app.services.supabase_service import supabase
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_fusion_report(country="China", limit=10):

    result = (
        supabase
        .table("risk_signals")
        .select("*")
        .eq("status", "new")
        .limit(limit)
        .execute()
    )

    signals = result.data

    if not signals:
        return {
            "status": "error",
            "message": "No signals found"
        }

    formatted_signals = []

    for signal in signals:

        formatted_signals.append({
            "title": signal.get("title"),
            "summary": signal.get("summary"),
            "severity": signal.get("severity"),
            "confidence": signal.get("confidence"),
            "domain": signal.get("domain"),
            "source": signal.get("source_provider")
        })

    prompt = f"""
You are Sovereign Intelligence.

Generate a professional geopolitical intelligence report for {country}.

Signals:
{formatted_signals}

Return:
- Executive Judgment
- Key Developments
- Strategic Assessment
- Cascading Effects
- Early Warning Indicators
- Decision Support
- Simulation Questions
"""

    response = client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": "You are an elite geopolitical fusion intelligence analyst."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    report = response.choices[0].message.content

    report = response.choices[0].message.content

    saved = supabase.table("fusion_reports").insert({
        "country": country,
        "title": f"{country} Fusion Intelligence Report",
        "report": report,
        "signal_count": len(signals),
        "model": "gpt-5.5"
    }).execute()

    return {
        "status": "success",
        "country": country,
        "signal_count": len(signals),
        "report": report,
        "saved_report": saved.data
    }
