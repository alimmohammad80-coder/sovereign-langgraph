from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import AgentSignal


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        normalized = str(value).strip()

        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        parsed = datetime.fromisoformat(normalized)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _freshness_score(signal: AgentSignal) -> float:
    if signal.is_live:
        return 100.0

    if signal.is_structural:
        return 65.0

    evidence_time = (
        signal.source_published_at
        or signal.event_time
        or signal.observation_date
    )

    parsed = _parse_datetime(evidence_time)

    if parsed is None:
        return 35.0

    age_days = max(
        0.0,
        (
            datetime.now(timezone.utc) - parsed
        ).total_seconds()
        / 86400,
    )

    if age_days <= 1:
        return 100.0
    if age_days <= 7:
        return 90.0
    if age_days <= 30:
        return 75.0
    if age_days <= 90:
        return 55.0
    if age_days <= 365:
        return 35.0

    return 20.0


class EvidenceScorer:
    """Calculate the SIAM Evidence Quality Score for each signal."""

    @staticmethod
    def run(
        signals: list[AgentSignal],
        context: dict[str, Any] | None = None,
    ) -> list[AgentSignal]:
        for signal in signals:
            corroboration_count = max(
                1,
                int(
                    getattr(
                        signal,
                        "siam_corroboration_count",
                        1,
                    )
                    or 1
                ),
            )

            corroboration_score = min(
                100.0,
                corroboration_count * 20.0,
            )

            freshness_score = _freshness_score(signal)

            quality_score = (
                float(signal.materiality_score or 0) * 0.25
                + float(signal.severity or 0) * 0.15
                + float(signal.relevance or 0) * 0.20
                + float(signal.source_reliability or 0) * 0.15
                + float(signal.confidence or 0) * 0.10
                + freshness_score * 0.10
                + corroboration_score * 0.05
            )

            setattr(
                signal,
                "siam_freshness_score",
                round(freshness_score, 2),
            )
            setattr(
                signal,
                "siam_corroboration_score",
                round(corroboration_score, 2),
            )
            setattr(
                signal,
                "siam_quality_score",
                round(
                    max(0.0, min(100.0, quality_score)),
                    2,
                ),
            )

        return signals
