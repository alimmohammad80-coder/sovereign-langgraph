def analyze_supply_chain_events(
    country=None,
    sector=None,
    chokepoint=None,
    commodity=None,
    live_articles=None,
    extracted_signals=None,
    live_signals=None
):
    live_articles = live_articles or []
    extracted_signals = extracted_signals or []
    live_signals = live_signals or {}

    active_signal_names = [
        key.replace("_", " ")
        for key, value in live_signals.items()
        if value
    ]

    article_titles = [
        article.get("title")
        for article in live_articles
        if article.get("title")
    ]

    event_count = len(live_articles)
    signal_count = len(extracted_signals)

    severity = 0
    reasons = []

    if event_count >= 5:
        severity += 15
        reasons.append("multiple live reports detected")

    if signal_count >= 3:
        severity += 20
        reasons.append("multiple supply-chain indicators extracted")

    if live_signals.get("military_escalation"):
        severity += 20
        reasons.append("military escalation signal detected")

    if live_signals.get("port_disruption"):
        severity += 18
        reasons.append("port or chokepoint disruption signal detected")

    if live_signals.get("sanctions_expansion"):
        severity += 15
        reasons.append("sanctions or restrictions signal detected")

    if live_signals.get("export_controls"):
        severity += 15
        reasons.append("export-control signal detected")

    if live_signals.get("price_spike"):
        severity += 10
        reasons.append("price spike or shortage signal detected")

    if sector == "semiconductors":
        severity += 10
        reasons.append("semiconductor sector is highly sensitive to disruption")

    if sector == "energy":
        severity += 10
        reasons.append("energy sector is highly exposed to chokepoint disruption")

    if chokepoint in ["Taiwan Strait", "Strait of Hormuz", "Bab el-Mandeb", "Suez Canal"]:
        severity += 12
        reasons.append(f"{chokepoint} is a strategic chokepoint")

    severity = min(100, severity)

    if severity >= 80:
        event_level = "Severe"
    elif severity >= 60:
        event_level = "High"
    elif severity >= 40:
        event_level = "Elevated"
    elif severity >= 20:
        event_level = "Watch"
    else:
        event_level = "Low"

    if event_count == 0:
        live_event_analysis = (
            "No live supply-chain events were detected from available feeds. "
            "Assessment should rely on structural exposure and monitoring until live feeds return signals."
        )
    else:
        live_event_analysis = (
            f"{event_count} live reports and {signal_count} extracted indicators were detected. "
            f"The current event-driven supply-chain risk level is {event_level.lower()}. "
            f"Key analytical reasons include: {', '.join(reasons[:4]) if reasons else 'limited confirmed disruption indicators'}."
        )

    cascading_effects = []

    if sector == "energy" or chokepoint in ["Strait of Hormuz", "Bab el-Mandeb", "Suez Canal"]:
        cascading_effects.extend([
            "Higher tanker insurance premiums",
            "Energy-price volatility",
            "Shipping rerouting and delivery delays"
        ])

    if sector == "semiconductors" or chokepoint == "Taiwan Strait":
        cascading_effects.extend([
            "Advanced chip delivery delays",
            "Electronics manufacturing disruption",
            "Export-control escalation risk"
        ])

    if live_signals.get("port_disruption"):
        cascading_effects.append("Port congestion and longer lead times")

    if live_signals.get("sanctions_expansion"):
        cascading_effects.append("Restricted access to sanctioned firms, vessels, or financial channels")

    if not cascading_effects:
        cascading_effects = [
            "Localized disruption risk",
            "Monitoring required for escalation",
            "Limited immediate systemic impact detected"
        ]

    return {
        "event_level": event_level,
        "event_severity_score": severity,
        "event_count": event_count,
        "signal_count": signal_count,
        "active_signal_names": active_signal_names,
        "live_event_analysis": live_event_analysis,
        "cascading_effects": cascading_effects,
        "source_titles_used": article_titles[:5],
        "analytic_reasons": reasons
    }
