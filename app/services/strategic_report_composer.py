from datetime import datetime
import json


def select_trigger_event(signals, country=None, topic=None):
    if isinstance(signals, list) and signals:
        for s in signals:
            if isinstance(s, dict) and s.get("title"):
                return {
                    "date": s.get("published_at") or s.get("date") or str(datetime.utcnow().date()),
                    "title": s.get("title"),
                    "source": s.get("source") or s.get("domain") or "Open Source",
                    "url": s.get("url"),
                    "summary": s.get("summary") or ""
                }

    return {
        "date": str(datetime.utcnow().date()),
        "title": "No verified triggering development identified from live sources.",
        "source": "Sovereign Intelligence",
        "url": None,
        "summary": ""
    }


def build_strategic_early_warning_prompt(
    entity,
    indicator,
    risk_score,
    risk_level,
    confidence,
    time_horizon,
    trigger_event=None,
    signals=None,
):
    trigger_event = trigger_event or {}
    signals = signals or []

    signal_titles = []
    for s in signals[:8]:
        if isinstance(s, dict):
            signal_titles.append({
                "title": s.get("title"),
                "source": s.get("source") or s.get("domain"),
                "published_at": s.get("published_at") or s.get("date"),
                "url": s.get("url")
            })

    return f"""
You are Sovereign Intelligence's senior strategic early-warning analyst.

Produce a concise but high-quality intelligence report in STRICT JSON only.
Do not include markdown. Do not include commentary outside JSON.

Country/entity: {entity}
Indicator/topic: {indicator}
Warning score: {risk_score}/100
Warning level: {risk_level}
Confidence: {confidence}
Time horizon: {time_horizon}

Trigger event:
{json.dumps(trigger_event, ensure_ascii=False, indent=2)}

Key open-source signals:
{json.dumps(signal_titles, ensure_ascii=False, indent=2)}

Analytic requirements:
- Write like a senior intelligence analyst, not a template.
- Explain why the warning score is not higher or lower.
- Distinguish persistent baseline pressure from acute escalation.
- Mention uncertainty and intelligence gaps.
- Keep each field focused and decision-useful.
- Return only this JSON structure:

{{
  "bluf": "...",
  "current_situation": "...",
  "strategic_assessment": "...",
  "forecast_outlook": "...",
  "operational_implications": "..."
}}
""".strip()


def validate_report(report):
    if not isinstance(report, dict):
        report = {}

    defaults = {
        "bluf": "No BLUF provided.",
        "current_situation": "Current situation not provided.",
        "strategic_assessment": "Strategic assessment not provided.",
        "forecast_outlook": "Forecast outlook not provided.",
        "operational_implications": "Operational implications not provided."
    }

    for k, v in defaults.items():
        if not report.get(k):
            report[k] = v

    return report
