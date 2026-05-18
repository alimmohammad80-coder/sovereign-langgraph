def generate_conflict_forecast(scoring, signals, timeframe="30d"):
    """
    Converts conflict score + signal pattern into dynamic forecast probabilities.
    This is a rule-based forecasting layer v1. Later we can blend it with ML/LLM analysis.
    """

    score = scoring.get("risk_score", 0)
    level = scoring.get("risk_level", "Stable")

    armed_clashes = signals.get("armed_clashes", 0)
    civil_unrest = signals.get("civil_unrest", 0)
    terrorism = signals.get("terrorism_activity", 0)
    refugee_flows = signals.get("refugee_flows", 0)
    cyber = signals.get("cyber_operations", 0)
    military = signals.get("military_pressure", 0)
    border = signals.get("border_incidents", 0)
    maritime = signals.get("maritime_incidents", 0)
    sanctions = signals.get("sanctions_pressure", False)

    kinetic = armed_clashes >= 8
    displacement = refugee_flows >= 100000
    gray_zone_pressure = military >= 7 or cyber >= 7 or maritime >= 7 or border >= 7
    convergence = 0

    if military >= 7 and cyber >= 6:
        convergence += 1
    if military >= 7 and border >= 6:
        convergence += 1
    if military >= 7 and maritime >= 6:
        convergence += 1
    if armed_clashes >= 8 and refugee_flows >= 50000:
        convergence += 1
    if sanctions and military >= 6:
        convergence += 1

    base_7d = round(score * 0.35)
    base_30d = round(score * 0.58)
    base_90d = round(score * 0.72)
    base_12m = round(score * 0.78)

    if kinetic:
        base_7d += 12
        base_30d += 10
        base_90d += 8

    if displacement:
        base_30d += 8
        base_90d += 10
        base_12m += 8

    if gray_zone_pressure:
        base_7d += 6
        base_30d += 8
        base_90d += 6

    if convergence >= 2:
        base_7d += 5
        base_30d += 8
        base_90d += 9
        base_12m += 6

    if civil_unrest >= 8:
        base_30d += 5
        base_90d += 6

    if terrorism >= 5:
        base_7d += 5
        base_30d += 6

    # Keep forecasts realistic
    if not kinetic and not displacement:
        base_7d = min(base_7d, 42)
        base_30d = min(base_30d, 67)
        base_90d = min(base_90d, 78)
        base_12m = min(base_12m, 82)

    forecast = {
        "7d_probability": max(0, min(base_7d, 95)),
        "30d_probability": max(0, min(base_30d, 95)),
        "90d_probability": max(0, min(base_90d, 95)),
        "12m_probability": max(0, min(base_12m, 95)),
        "forecast_level": level,
        "forecast_logic": {
            "kinetic_activity_present": kinetic,
            "mass_displacement_present": displacement,
            "gray_zone_pressure_present": gray_zone_pressure,
            "escalation_convergence_count": convergence
        }
    }

    return forecast
