def generate_simulation_questions(country, scoring, forecast):
    level = scoring.get("risk_level", "Stable")
    score = scoring.get("risk_score", 0)
    logic = forecast.get("forecast_logic", {})

    kinetic = logic.get("kinetic_activity_present", False)
    gray_zone = logic.get("gray_zone_pressure_present", False)
    convergence = logic.get("escalation_convergence_count", 0)

    if level == "Acute" or kinetic:
        return [
            f"What if {country}'s conflict intensity expands over the next 30 days?",
            f"Which regional actors are most likely to intervene or exploit the crisis in {country}?",
            f"What are the second-order effects on energy, supply chains, refugees, and markets?"
        ]

    if level == "Crisis" and gray_zone:
        return [
            f"What if gray-zone pressure against {country} crosses into limited kinetic action?",
            f"How would cyber, maritime, and military escalation affect regional stability?",
            f"What indicators would confirm movement from crisis pressure to open conflict?"
        ]

    if level == "Warning":
        return [
            f"What if warning indicators in {country} converge over the next 30 days?",
            f"Which trigger would most likely shift {country} from warning to crisis?",
            f"What monitoring priorities should analysts track first?"
        ]

    if level == "Watch":
        return [
            f"What if early warning signals in {country} intensify?",
            f"Which indicators would justify raising {country}'s risk level?",
            f"What low-probability shock could change the forecast?"
        ]

    return [
        f"What unexpected shock could destabilize {country}?",
        f"Which baseline indicators should be monitored for change?",
        f"What would move {country} from stable to watch?"
    ]
