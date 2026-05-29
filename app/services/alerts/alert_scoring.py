def calculate_severity(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 45:
        return "moderate"
    return "low"


def calculate_velocity(score: int, domains: list[str]) -> str:
    if score >= 80 and len(domains) >= 2:
        return "rapidly rising"
    if score >= 65:
        return "rising"
    if score >= 45:
        return "watch"
    return "stable"


def calculate_confidence(signal_count: int, source_count: int = 1) -> str:
    if signal_count >= 4 and source_count >= 3:
        return "high"
    if signal_count >= 2:
        return "medium"
    return "low"
