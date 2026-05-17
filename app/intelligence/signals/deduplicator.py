from typing import List
from app.intelligence.schemas import IntelligenceSignal


def deduplicate_signals(signals: List[IntelligenceSignal]) -> List[IntelligenceSignal]:
    seen = set()
    unique = []

    for signal in signals:
        key = signal.title.lower().strip()

        # Remove publisher suffix noise where possible
        if " - " in key:
            key = key.split(" - ")[0].strip()

        if key in seen:
            continue

        seen.add(key)
        unique.append(signal)

    return unique
