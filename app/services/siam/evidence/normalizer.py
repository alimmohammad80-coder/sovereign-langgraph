from __future__ import annotations

from typing import Any

from app.agents.base_agent import AgentSignal


_DIRECTION_MAP = {
    "up": "deteriorating",
    "rising": "deteriorating",
    "worsening": "deteriorating",
    "negative": "deteriorating",
    "down": "improving",
    "falling": "improving",
    "positive": "improving",
    "unchanged": "stable",
    "neutral": "stable",
    "stable": "stable",
    "mixed": "mixed",
    "unknown": "unknown",
}


class EvidenceNormalizer:
    """Normalize evidence fields without changing collector interfaces."""

    @staticmethod
    def run(
        signals: list[AgentSignal],
        context: dict[str, Any] | None = None,
    ) -> list[AgentSignal]:
        safe_context = context or {}
        region = str(
            safe_context.get("region") or ""
        ).strip() or None

        for signal in signals:
            signal.signal_id = str(signal.signal_id).strip()
            signal.domain = str(signal.domain).strip().lower()
            signal.signal_type = (
                str(signal.signal_type or "unknown")
                .strip()
                .lower()
            )
            signal.headline = " ".join(
                str(signal.headline).split()
            )

            if signal.summary:
                signal.summary = " ".join(
                    str(signal.summary).split()
                )

            if signal.country_iso3:
                signal.country_iso3 = (
                    str(signal.country_iso3)
                    .strip()
                    .upper()
                )

            if signal.country_name:
                signal.country_name = " ".join(
                    str(signal.country_name).split()
                )

            if region:
                signal.region = region
            elif signal.region:
                signal.region = " ".join(
                    str(signal.region).split()
                )

            raw_direction = (
                str(signal.direction or "unknown")
                .strip()
                .lower()
            )
            signal.direction = _DIRECTION_MAP.get(
                raw_direction,
                "unknown",
            )

            signal.tags = sorted(
                {
                    str(tag).strip().lower()
                    for tag in signal.tags
                    if str(tag).strip()
                }
            )

        return signals
