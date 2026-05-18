def generate_executive_judgment(country, scoring, forecast):
    level = scoring.get("risk_level", "Stable")
    logic = forecast.get("forecast_logic", {})

    kinetic = logic.get("kinetic_activity_present", False)
    gray_zone = logic.get("gray_zone_pressure_present", False)

    if level == "Acute":
        return f"{country}: Acute conflict risk. Active kinetic pressure and displacement indicators suggest sustained escalation risk."

    if level == "Crisis" and gray_zone:
        return f"{country}: Crisis-level pressure. No major kinetic conflict detected, but gray-zone and military indicators show escalation convergence."

    if level == "Warning":
        return f"{country}: Warning-level instability. Multiple pressure indicators are active, but escalation remains contained."

    if level == "Watch":
        return f"{country}: Watch-level risk. Early warning signals are present but not yet converging into crisis conditions."

    return f"{country}: Stable. No major conflict escalation indicators detected."
