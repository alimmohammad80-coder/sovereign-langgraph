from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.agents.base_agent import AgentSignal


def _priority(signal: AgentSignal) -> tuple[float, float, float, float, float]:
    return (
        float(signal.materiality_score or 0),
        float(signal.severity or 0),
        float(signal.relevance or 0),
        float(signal.source_reliability or 0),
        float(signal.confidence or 0),
    )


class RegionalEvidenceBalancer:
    """Limit country dominance while preserving critical evidence."""

    @staticmethod
    def run(
        signals: list[AgentSignal],
        context: dict[str, Any] | None = None,
    ) -> list[AgentSignal]:
        safe_context = context or {}

        per_country_limit = max(
            2,
            int(
                safe_context.get(
                    "regional_country_signal_limit",
                    6,
                )
            ),
        )

        grouped: dict[str, list[AgentSignal]] = defaultdict(list)

        for signal in signals:
            country_key = (
                signal.country_iso3
                or signal.country_name
                or "REGIONAL_OR_UNKNOWN"
            )
            grouped[str(country_key)].append(signal)

        balanced: list[AgentSignal] = []

        for country_signals in grouped.values():
            ranked = sorted(
                country_signals,
                key=_priority,
                reverse=True,
            )

            selected = ranked[:per_country_limit]

            critical_outliers = [
                signal
                for signal in ranked[per_country_limit:]
                if (
                    float(signal.materiality_score or 0) >= 90
                    or float(signal.severity or 0) >= 90
                )
            ][:2]

            for signal in critical_outliers:
                setattr(
                    signal,
                    "siam_balance_override",
                    "critical_outlier",
                )

            balanced.extend(selected)
            balanced.extend(critical_outliers)

        return balanced
