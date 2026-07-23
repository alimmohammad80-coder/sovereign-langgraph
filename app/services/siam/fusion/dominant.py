from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DominantDomainResult:
    leading_domain: str | None
    leading_domain_label: str | None
    leading_risk_score: float
    supporting_domains: list[str]
    ranked_domains: list[dict[str, Any]]


class DominantDomainAnalyzer:
    """
    Identifies the leading and supporting domains in a set of
    authoritative regional assessments.

    This analyzer does not recalculate domain risk. It preserves the
    supplied deterministic scores and only ranks them.
    """

    DEFAULT_SUPPORTING_THRESHOLD = 50.0
    DEFAULT_SUPPORTING_DISTANCE = 20.0

    @staticmethod
    def _as_score(value: Any) -> float:
        try:
            return max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _domain_key(
        assessment: dict[str, Any],
    ) -> str:
        return str(
            assessment.get("sector")
            or assessment.get("agent_key")
            or assessment.get("domain")
            or "unknown"
        ).strip()

    @classmethod
    def _domain_label(
        cls,
        assessment: dict[str, Any],
    ) -> str:
        return str(
            assessment.get("sector_label")
            or assessment.get("domain_label")
            or cls._domain_key(assessment)
        ).strip()

    def analyze(
        self,
        assessments: Iterable[dict[str, Any]],
    ) -> DominantDomainResult:
        normalized: list[dict[str, Any]] = []

        for assessment in assessments:
            if not isinstance(assessment, dict):
                continue

            domain = self._domain_key(assessment)

            if not domain or domain == "unknown":
                continue

            normalized.append(
                {
                    "domain": domain,
                    "domain_label": self._domain_label(
                        assessment
                    ),
                    "risk_score": self._as_score(
                        assessment.get("risk_score")
                    ),
                    "confidence": self._as_score(
                        assessment.get("confidence")
                    ),
                    "risk_level": assessment.get(
                        "risk_level"
                    ),
                    "bluf": assessment.get("bluf"),
                }
            )

        ranked = sorted(
            normalized,
            key=lambda item: (
                item["risk_score"],
                item["confidence"],
            ),
            reverse=True,
        )

        if not ranked:
            return DominantDomainResult(
                leading_domain=None,
                leading_domain_label=None,
                leading_risk_score=0.0,
                supporting_domains=[],
                ranked_domains=[],
            )

        leader = ranked[0]
        leading_score = float(
            leader["risk_score"]
        )

        supporting_domains = [
            item["domain"]
            for item in ranked[1:]
            if (
                item["risk_score"]
                >= self.DEFAULT_SUPPORTING_THRESHOLD
                and leading_score - item["risk_score"]
                <= self.DEFAULT_SUPPORTING_DISTANCE
            )
        ]

        return DominantDomainResult(
            leading_domain=leader["domain"],
            leading_domain_label=leader[
                "domain_label"
            ],
            leading_risk_score=leading_score,
            supporting_domains=supporting_domains,
            ranked_domains=ranked,
        )
