from typing import List
from app.intelligence.schemas import IntelligenceSignal


HIGH_RISK_KEYWORDS = [
    "military",
    "missile",
    "attack",
    "conflict",
    "sanctions",
    "blockade",
    "cyberattack",
    "war",
    "mobilization",
    "naval",
    "airstrike",
    "crisis",
    "escalation",
]

MEDIUM_RISK_KEYWORDS = [
    "pressure",
    "warning",
    "exercise",
    "tariff",
    "restriction",
    "disruption",
    "tension",
    "risk",
    "deployment",
]


def calculate_signal_severity(signal: IntelligenceSignal) -> int:
    text = f"{signal.title} {signal.summary}".lower()

    score = 40

    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in text:
            score += 10

    for keyword in MEDIUM_RISK_KEYWORDS:
        if keyword in text:
            score += 5

    return min(score, 100)


def score_signals(signals: List[IntelligenceSignal]) -> List[IntelligenceSignal]:
    scored_signals = []

    for signal in signals:
        signal.severity = calculate_signal_severity(signal)

        if signal.severity >= 80:
            signal.confidence = "High"
        elif signal.severity >= 60:
            signal.confidence = "Moderate-High"
        else:
            signal.confidence = "Moderate"

        scored_signals.append(signal)

    return scored_signals


def calculate_overall_warning_score(signals: List[IntelligenceSignal]) -> int:
    if not signals:
        return 0

    total = sum(signal.severity for signal in signals)
    return int(total / len(signals))


def determine_warning_level(score: int) -> str:
    if score >= 85:
        return "Critical"
    elif score >= 70:
        return "High"
    elif score >= 55:
        return "Elevated"
    elif score >= 40:
        return "Guarded"
    else:
        return "Low"
