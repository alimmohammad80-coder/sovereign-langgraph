def classify_level(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 50:
        return "Elevated"
    if score >= 30:
        return "Watch"
    return "Stable"


def generate_forecast(score: int, convergence: int):
    return {
        "7d": min(100, round(score * 0.65 + convergence * 4)),
        "30d": min(100, round(score * 0.85 + convergence * 5)),
        "90d": min(100, round(score * 0.95 + convergence * 4)),
        "12m": min(100, round(score * 0.9 + convergence * 3)),
    }


def executive_judgment(country, sector, chokepoint, level, score, drivers):
    location = f" through {chokepoint}" if chokepoint else ""
    top = ", ".join(drivers[:3]) if drivers else "limited confirmed disruption indicators"
    return (
        f"{country}: {level} supply-chain risk in {sector}{location}. "
        f"Risk score {score}/100 is driven by {top}."
    )


def recommended_actions(level, sector):
    base = [
        "Map first-, second-, and third-tier supplier exposure.",
        "Monitor sanctions, transport disruption, insurance, and commodity-price signals.",
        "Identify alternative suppliers, routes, and stockpiling options.",
        "Run scenario simulation for 7-day, 30-day, and 90-day disruption windows."
    ]

    if level in ["High", "Critical"]:
        base.insert(0, "Activate executive supply-chain risk review immediately.")
        base.append("Prepare customer, investor, and operational continuity communications.")

    if sector == "semiconductors":
        base.append("Assess exposure to Taiwan fabs, advanced packaging, rare gases, and export controls.")
    if sector == "energy":
        base.append("Track crude, LNG, tanker insurance, refinery outages, and strategic reserve policy.")
    if sector == "food_security":
        base.append("Track grain corridors, fertilizer access, weather shocks, and food-price inflation.")

    return base


def simulation_questions(country, sector, chokepoint):
    place = chokepoint or country
    return [
        f"What happens if {place} faces a 7-day disruption?",
        f"What are the 30-day second-order effects on {sector} markets?",
        "Which countries, firms, or ports are most exposed?",
        "What alternative suppliers or routes reduce exposure?",
        "What escalation pathway would turn this into a systemic crisis?"
    ]
