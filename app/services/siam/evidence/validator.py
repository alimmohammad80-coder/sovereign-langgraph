from __future__ import annotations

from typing import Any

from app.agents.base_agent import AgentSignal


def _bounded_score(value: Any) -> float:
    score = float(value or 0)
    return max(0.0, min(100.0, score))


class EvidenceValidator:
    """Validate and safely bound collector-produced evidence signals."""

    @staticmethod
    def run(
        signals: list[AgentSignal],
        context: dict[str, Any] | None = None,
    ) -> list[AgentSignal]:
        validated: list[AgentSignal] = []

        for signal in signals:
            if not isinstance(signal, AgentSignal):
                continue

            if not str(signal.signal_id or "").strip():
                continue

            if not str(signal.domain or "").strip():
                continue

            if not str(signal.signal_type or "").strip():
                continue

            if not str(signal.headline or "").strip():
                continue

            try:
                signal.severity = _bounded_score(signal.severity)
                signal.relevance = _bounded_score(signal.relevance)
                signal.confidence = _bounded_score(signal.confidence)
                signal.source_reliability = _bounded_score(
                    signal.source_reliability
                )
                signal.materiality_score = _bounded_score(
                    signal.materiality_score
                )
            except (TypeError, ValueError):
                continue

            validated.append(signal)

        return validated
