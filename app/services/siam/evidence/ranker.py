from __future__ import annotations

from typing import Any

from app.agents.base_agent import AgentSignal


class EvidenceRanker:
    """Rank processed evidence by SIAM quality and strategic importance."""

    @staticmethod
    def run(
        signals: list[AgentSignal],
        context: dict[str, Any] | None = None,
    ) -> list[AgentSignal]:
        safe_context = context or {}

        regional_limit = max(
            10,
            int(
                safe_context.get(
                    "regional_signal_limit",
                    60,
                )
            ),
        )

        ranked = sorted(
            signals,
            key=lambda signal: (
                float(
                    getattr(
                        signal,
                        "siam_quality_score",
                        0,
                    )
                    or 0
                ),
                float(signal.materiality_score or 0),
                float(signal.severity or 0),
                float(signal.relevance or 0),
                float(signal.source_reliability or 0),
                float(signal.confidence or 0),
            ),
            reverse=True,
        )

        return ranked[:regional_limit]
