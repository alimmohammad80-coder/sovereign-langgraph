from typing import List, Dict, Any
from app.intelligence.schemas import IntelligenceSignal


def normalize_raw_items(raw_items: List[Dict[str, Any]]) -> List[IntelligenceSignal]:
    signals = []

    for item in raw_items:
        title = item.get("title") or item.get("headline") or "Untitled signal"

        summary = (
            item.get("summary")
            or item.get("description")
            or item.get("snippet")
            or ""
        )

        source = item.get("source") or item.get("publisher") or "Unknown source"
        url = item.get("url") or item.get("link")
        domain = item.get("domain") or item.get("category") or "general"

        signals.append(
            IntelligenceSignal(
                title=title,
                summary=summary,
                source=source,
                url=url,
                domain=domain,
                severity=50,
                confidence="Moderate",
            )
        )

    return signals
