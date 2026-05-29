def build_launch_context(alert: dict, module: str) -> dict:
    countries = alert.get("countries", [])
    sectors = alert.get("sectors", [])
    chokepoints = alert.get("chokepoints", [])
    domains = alert.get("domains", [])
    signals = alert.get("signals", [])

    country = countries[0] if countries else None
    sector = sectors[0] if sectors else None
    chokepoint = chokepoints[0] if chokepoints else None

    base = {
        "alert_id": alert.get("alert_id"),
        "title": alert.get("title"),
        "risk_score": alert.get("risk_score"),
        "severity": alert.get("severity"),
        "domains": domains,
        "signals": signals,
    }

    if module == "conflict_forecasting":
        return {
            **base,
            "country": country,
            "region": chokepoint or country,
            "indicator": "Military Escalation",
            "timeframe": "30d",
            "limit": 5,
        }

    if module == "supply_chain":
        return {
            **base,
            "selected_country": country,
            "selected_sector": sector,
            "selected_chokepoint": chokepoint,
            "selected_commodity": sector,
        }

    if module == "strategic_early_warning":
        return {
            **base,
            "entity": country or chokepoint or alert.get("title"),
            "indicator": "Cross-Domain Escalation",
            "limit": 8,
        }

    if module == "scenario_simulation":
        return {
            **base,
            "scenario": f"What happens if {alert.get('title')} escalates over the next 30-90 days?",
            "time_horizon": "30-90 days",
            "affected_domains": domains,
        }

    if module == "knowledge_graph":
        return {
            **base,
            "entity": country or chokepoint or sector or alert.get("title"),
        }

    return base
