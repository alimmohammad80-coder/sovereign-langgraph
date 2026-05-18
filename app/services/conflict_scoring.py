def calculate_conflict_score(signals):
    score = 0
    drivers = []

    armed_clashes = signals.get("armed_clashes", 0)
    civil_unrest = signals.get("civil_unrest", 0)
    terrorism = signals.get("terrorism_activity", 0)
    sanctions = signals.get("sanctions_pressure", False)
    refugee_flows = signals.get("refugee_flows", 0)
    cyber_activity = signals.get("cyber_operations", 0)
    military_pressure = signals.get("military_pressure", 0)
    border_incidents = signals.get("border_incidents", 0)
    maritime_incidents = signals.get("maritime_incidents", 0)

    # Kinetic conflict
    score += min(armed_clashes * 3, 25)
    if armed_clashes >= 10:
        drivers.append("High armed-clash activity")
    elif armed_clashes >= 5:
        drivers.append("Moderate armed-clash activity")

    # Civil unrest
    score += min(civil_unrest * 2, 18)
    if civil_unrest >= 8:
        drivers.append("Elevated civil unrest")
    elif civil_unrest >= 4:
        drivers.append("Moderate civil unrest")

    # Terrorism / militant activity
    score += min(terrorism * 3, 15)
    if terrorism >= 5:
        drivers.append("High terrorism or militant activity")
    elif terrorism >= 2:
        drivers.append("Emerging terrorism or militant activity")

    # Sanctions / coercive pressure
    if sanctions:
        score += 8
        drivers.append("Sanctions or coercive economic pressure")

    # Refugee / displacement pressure
    if refugee_flows >= 500000:
        score += 15
        drivers.append("Severe refugee or displacement pressure")
    elif refugee_flows >= 100000:
        score += 10
        drivers.append("Major refugee or displacement pressure")
    elif refugee_flows >= 25000:
        score += 5
        drivers.append("Emerging displacement pressure")

    # Cyber operations
    score += min(cyber_activity * 2, 14)
    if cyber_activity >= 7:
        drivers.append("High cyber-operational pressure")
    elif cyber_activity >= 4:
        drivers.append("Moderate cyber-operational pressure")

    # Military pressure
    score += min(military_pressure * 3, 24)
    if military_pressure >= 8:
        drivers.append("Severe military pressure")
    elif military_pressure >= 5:
        drivers.append("Elevated military pressure")

    # Border incidents
    score += min(border_incidents * 2, 16)
    if border_incidents >= 7:
        drivers.append("Frequent border incidents")
    elif border_incidents >= 4:
        drivers.append("Moderate border incidents")

    # Maritime incidents
    score += min(maritime_incidents * 2, 16)
    if maritime_incidents >= 7:
        drivers.append("High maritime escalation risk")
    elif maritime_incidents >= 4:
        drivers.append("Moderate maritime escalation risk")

    # Compound escalation bonus
    if military_pressure >= 7 and cyber_activity >= 6:
        score += 8
        drivers.append("Military-cyber escalation convergence")

    if border_incidents >= 6 and military_pressure >= 7:
        score += 7
        drivers.append("Border-military escalation convergence")

    if maritime_incidents >= 6 and military_pressure >= 7:
        score += 7
        drivers.append("Maritime-military escalation convergence")

    if armed_clashes >= 10 and refugee_flows >= 100000:
        score += 8
        drivers.append("Kinetic conflict and displacement convergence")

    # Cap score for non-kinetic pressure scenarios
    has_kinetic_crisis = armed_clashes >= 10 or refugee_flows >= 100000

    if not has_kinetic_crisis:
        score = min(score, 82)

    score = min(round(score), 100)

    has_kinetic_crisis = armed_clashes >= 10 or refugee_flows >= 100000
    has_extreme_pressure = military_pressure >= 9 and (border_incidents >= 8 or maritime_incidents >= 8)

    if score >= 85 and has_kinetic_crisis:
        level = "Acute"
    elif score >= 75 and (has_kinetic_crisis or has_extreme_pressure):
        level = "Crisis"
    elif score >= 50:
        level = "Warning"
    elif score >= 30:
        level = "Watch"
    else:
        level = "Stable"

    return {
        "risk_score": score,
        "risk_level": level,
        "risk_drivers": drivers
    }
