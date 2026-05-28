from datetime import datetime

def select_trigger_event(signals, country=None, topic=None):
    """
    Selects the best trigger event from available signals.
    Falls back safely if no verified live signal exists.
    """
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


def validate_report(report):
    """
    Ensures Gemini/fallback report always has required fields.
    """
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
