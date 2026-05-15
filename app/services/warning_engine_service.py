from app.services.supabase_service import supabase


def classify_warning_level(avg_severity):
    if avg_severity >= 85:
        return "CRITICAL"
    if avg_severity >= 70:
        return "WARNING"
    if avg_severity >= 55:
        return "WATCH"
    return "MONITOR"


def generate_strategic_warning(country="China", limit=10):
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
            "message": "No active risk signals found"
        }

    severities = [
        int(signal.get("severity") or 0)
        for signal in signals
    ]

    avg_severity = int(sum(severities) / len(severities))
    warning_level = classify_warning_level(avg_severity)

    drivers = [
        signal.get("title")
        for signal in signals[:5]
    ]

    warning = {
        "country": country,
        "region": "Global / Indo-Pacific",
        "warning_level": warning_level,
        "probability": avg_severity,
        "confidence": 70,
        "title": f"{country} Strategic Warning: {warning_level}",
        "drivers": drivers,
        "indicators": [
            "Rising volume of geopolitical risk signals",
            "Cross-domain pressure across security, energy, and diplomacy",
            "Potential escalation pathways requiring monitoring"
        ],
        "recommended_actions": [
            "Maintain enhanced monitoring",
            "Review latest fusion report",
            "Track military, energy, and diplomatic indicators",
            "Prepare scenario simulation"
        ]
    }

    saved = (
        supabase
        .table("strategic_warnings")
        .insert(warning)
        .execute()
    )

    return {
        "status": "success",
        "warning": warning,
        "saved": saved.data
    }
