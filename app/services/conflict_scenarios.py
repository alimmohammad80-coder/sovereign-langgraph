def generate_conflict_scenarios(country, scoring, forecast):
    level = scoring.get("risk_level", "Stable")
    logic = forecast.get("forecast_logic", {})

    kinetic = logic.get("kinetic_activity_present", False)
    displacement = logic.get("mass_displacement_present", False)
    gray_zone = logic.get("gray_zone_pressure_present", False)

    if level == "Acute" or kinetic or displacement:
        return {
            "best_case": "Containment through ceasefire pressure, external mediation, and reduced operational tempo.",
            "likely_case": "Sustained conflict with periodic escalation, civilian disruption, and regional spillover risk.",
            "worst_case": "Expanded conflict, wider displacement, infrastructure damage, and direct external involvement."
        }

    if level == "Crisis" and gray_zone:
        return {
            "best_case": "Pressure stabilizes below kinetic threshold through deterrence and diplomatic signaling.",
            "likely_case": "Gray-zone operations persist with cyber, maritime, and military pressure below open conflict.",
            "worst_case": "Miscalculation triggers limited kinetic escalation or blockade-style coercion."
        }

    if level == "Warning":
        return {
            "best_case": "Warning indicators recede and instability remains politically contained.",
            "likely_case": "Localized instability continues without broader escalation.",
            "worst_case": "Multiple warning indicators converge into crisis conditions."
        }

    if level == "Watch":
        return {
            "best_case": "Signals remain isolated and do not develop into sustained instability.",
            "likely_case": "Low-level pressure continues with periodic alerts.",
            "worst_case": "Early indicators intensify into a warning-level instability pattern."
        }

    return {
        "best_case": "No material escalation observed.",
        "likely_case": "Stable conditions continue with routine monitoring.",
        "worst_case": "Unexpected shock produces localized instability."
    }
