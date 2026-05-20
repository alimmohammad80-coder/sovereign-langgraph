from app.data.supply_chain_catalog import CHOKEPOINTS, COUNTRY_EXPOSURE


def calculate_supply_chain_risk(country, sector, chokepoint=None, commodity=None, custom_signals=None):
    custom_signals = custom_signals or {}

    score = 0
    drivers = []
    convergence = 0

    country_profile = COUNTRY_EXPOSURE.get(country, {
        "sanctions": 6,
        "geopolitical": 10,
        "manufacturing_dependency": 10
    })

    score += country_profile["sanctions"]
    score += country_profile["geopolitical"]
    score += country_profile["manufacturing_dependency"]

    if country_profile["sanctions"] >= 15:
        drivers.append("sanctions and export-control exposure")
        convergence += 1

    if country_profile["geopolitical"] >= 18:
        drivers.append("high geopolitical pressure")
        convergence += 1

    if country_profile["manufacturing_dependency"] >= 20:
        drivers.append("high manufacturing dependency")
        convergence += 1

    if chokepoint and chokepoint in CHOKEPOINTS:
        cp = CHOKEPOINTS[chokepoint]
        score += cp["base_risk"]
        drivers.append(f"strategic chokepoint exposure: {chokepoint}")
        convergence += 1

        if sector in cp["sectors"]:
            score += 12
            drivers.append(f"{sector} is directly exposed to {chokepoint}")
            convergence += 1

    sector_weights = {
        "energy": 12,
        "semiconductors": 15,
        "critical_minerals": 13,
        "food_security": 11,
        "maritime": 12,
        "pharmaceuticals": 9,
        "defense_industrial_base": 14
    }

    score += sector_weights.get(sector, 8)

    if commodity:
        score += 5
        drivers.append(f"commodity-specific exposure: {commodity}")

    signal_weights = {
        "port_disruption": 12,
        "military_escalation": 18,
        "sanctions_expansion": 15,
        "cyber_disruption": 12,
        "price_spike": 10,
        "insurance_premium_rise": 10,
        "export_controls": 14,
        "supplier_concentration": 13,
        "weather_disruption": 8,
        "labor_unrest": 6
    }

    active_signals = {}

    for signal, weight in signal_weights.items():
        value = bool(custom_signals.get(signal, False))
        active_signals[signal] = value
        if value:
            score += weight
            drivers.append(signal.replace("_", " "))
            convergence += 1

    score = min(100, max(0, round(score)))

    return {
        "score": score,
        "drivers": drivers,
        "convergence": convergence,
        "active_signals": active_signals
    }
