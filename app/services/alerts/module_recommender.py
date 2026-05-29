def recommend_modules(alert: dict) -> list[dict]:
    domains = alert.get("domains", [])
    text = f"{alert.get('title', '')} {alert.get('summary', '')}".lower()
    risk_score = int(alert.get("risk_score", 50) or 50)

    modules = []

    if "conflict" in domains or any(k in text for k in ["military", "drill", "missile", "border", "naval"]):
        modules.append({
            "module": "conflict_forecasting",
            "label": "Run Conflict Forecast",
            "reason": "Military, escalation, or conflict indicators detected.",
            "endpoint": "/api/conflict/run-forecast",
            "priority": 1
        })

    if "supply_chain" in domains or any(k in text for k in ["shipping", "port", "semiconductor", "strait", "chokepoint"]):
        modules.append({
            "module": "supply_chain",
            "label": "Analyze Supply Chain Exposure",
            "reason": "Trade, logistics, chokepoint, or sector exposure detected.",
            "endpoint": "/api/supply-chain/run-agent",
            "priority": 1
        })

    if "energy" in domains or any(k in text for k in ["oil", "gas", "lng", "pipeline", "hormuz"]):
        modules.append({
            "module": "geopolitical_risk",
            "label": "Assess Energy & Geopolitical Risk",
            "reason": "Energy route, commodity, or strategic market risk detected.",
            "endpoint": "/api/geopolitical-risk/run",
            "priority": 2
        })

    if "cyber" in domains:
        modules.append({
            "module": "strategic_early_warning",
            "label": "Open Cyber/Early Warning",
            "reason": "Cyber or information threat indicators detected.",
            "endpoint": "/api/early-warning/run",
            "priority": 2
        })

    if risk_score >= 65:
        modules.append({
            "module": "strategic_early_warning",
            "label": "Open Strategic Early Warning",
            "reason": "Alert score indicates elevated warning conditions.",
            "endpoint": "/api/early-warning/run",
            "priority": 1
        })

    modules.append({
        "module": "scenario_simulation",
        "label": "Simulate Scenario",
        "reason": "Model possible escalation pathways and second-order effects.",
        "endpoint": "/api/scenario/run",
        "priority": 3
    })

    modules.append({
        "module": "knowledge_graph",
        "label": "View Knowledge Graph",
        "reason": "Explore linked actors, sectors, chokepoints, and relationships.",
        "endpoint": "/api/knowledge-graph/overview",
        "priority": 4
    })

    seen = set()
    deduped = []
    for m in modules:
        if m["module"] not in seen:
            deduped.append(m)
            seen.add(m["module"])

    return sorted(deduped, key=lambda x: x["priority"])
