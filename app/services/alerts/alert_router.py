from app.services.alerts.signal_classifier import classify_signal
from app.services.alerts.entity_extractor import extract_entities
from app.services.alerts.module_recommender import recommend_modules
from app.services.alerts.alert_scoring import calculate_severity, calculate_velocity, calculate_confidence
from app.services.alerts.launch_context import build_launch_context


def orchestrate_alert(raw_alert: dict) -> dict:
    title = raw_alert.get("title", "Untitled Alert")
    summary = raw_alert.get("summary", raw_alert.get("description", ""))
    score = int(raw_alert.get("score", raw_alert.get("risk_score", 50)) or 50)

    domains = raw_alert.get("domains") or classify_signal(title, summary)
    extracted = extract_entities(title, summary)

    alert = {
        "alert_id": str(raw_alert.get("id") or raw_alert.get("alert_id") or abs(hash(title))),
        "title": title,
        "summary": summary,
        "severity": calculate_severity(score),
        "risk_score": score,
        "velocity": calculate_velocity(score, domains),
        "confidence": calculate_confidence(signal_count=1, source_count=1),
        "domains": domains,
        "entities": extracted["entities"],
        "countries": extracted["countries"],
        "sectors": extracted["sectors"],
        "chokepoints": extracted["chokepoints"],
        "signals": [
            {
                "title": title,
                "summary": summary,
                "source": raw_alert.get("source"),
                "url": raw_alert.get("url"),
                "score": score,
                "domain": domains[0] if domains else "geopolitical",
                "created_at": raw_alert.get("created_at") or raw_alert.get("published_at"),
            }
        ],
        "source_urls": [raw_alert.get("url")] if raw_alert.get("url") else [],
        "created_at": raw_alert.get("created_at") or raw_alert.get("published_at"),
    }

    alert["recommended_modules"] = recommend_modules(alert)

    alert["launch_contexts"] = {
        m["module"]: build_launch_context(alert, m["module"])
        for m in alert["recommended_modules"]
    }

    return alert
