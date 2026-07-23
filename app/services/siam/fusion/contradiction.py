from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable


@dataclass(frozen=True)
class ContradictionResult:
    contradiction_score: float
    contradictions: list[dict[str, Any]]


class ContradictionAnalyzer:
    """
    Detects analytical disagreement between domain assessments.

    A contradiction exists when domains present materially different
    trajectories or materially different risk states.
    """

    RISK_DELTA = 30.0

    @staticmethod
    def _score(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _direction(a: dict[str, Any]) -> str:
        return str(
            a.get("direction", "unknown")
        ).lower()

    @staticmethod
    def _domain(a: dict[str, Any]) -> str:
        return str(
            a.get("sector")
            or a.get("agent_key")
            or a.get("domain")
        )

    def analyze(
        self,
        assessments: Iterable[dict[str, Any]],
    ) -> ContradictionResult:

        items = list(assessments)

        contradictions = []

        for left, right in combinations(items, 2):

            risk_delta = abs(
                self._score(left.get("risk_score"))
                - self._score(right.get("risk_score"))
            )

            direction_conflict = (
                {
                    self._direction(left),
                    self._direction(right),
                }
                == {
                    "improving",
                    "deteriorating",
                }
            )

            if (
                risk_delta >= self.RISK_DELTA
                or direction_conflict
            ):
                contradictions.append(
                    {
                        "domains": [
                            self._domain(left),
                            self._domain(right),
                        ],
                        "risk_delta": round(
                            risk_delta,
                            1,
                        ),
                        "direction_conflict": direction_conflict,
                    }
                )

        score = min(
            100.0,
            len(contradictions) * 20,
        )

        return ContradictionResult(
            contradiction_score=score,
            contradictions=contradictions,
        )
