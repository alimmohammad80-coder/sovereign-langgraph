from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from app.services.siam.models.strategic_intelligence import (
    StrategicIntelligence,
)

from app.services.siam.fusion.dominant import (
    DominantDomainAnalyzer,
)
from app.services.siam.fusion.convergence import (
    ConvergenceAnalyzer,
)
from app.services.siam.fusion.contradiction import (
    ContradictionAnalyzer,
)
from app.services.siam.fusion.direction import (
    DirectionAnalyzer,
)
from app.services.siam.fusion.confidence import (
    ConfidenceCalibrator,
)
from app.services.siam.fusion.forecast import (
    ForecastFusion,
)


EXPECTED_DOMAINS = (
    "conflict_monitoring",
    "political_stability",
    "economic_risk",
    "energy_security",
    "trade_sanctions",
)


class SIAMFusionEngine:
    """
    Canonical SIAM cross-domain fusion engine.

    The engine orchestrates analytical components but does not replace
    or recalculate deterministic domain-agent assessments.

    Pipeline:

        authoritative regional assessments
                    ↓
        dominant-domain analysis
                    ↓
        convergence analysis
                    ↓
        contradiction analysis
                    ↓
        strategic direction
                    ↓
        confidence calibration
                    ↓
        forecast fusion
                    ↓
        StrategicIntelligence
    """

    def __init__(self) -> None:
        self.dominant = DominantDomainAnalyzer()
        self.convergence = ConvergenceAnalyzer()
        self.contradiction = ContradictionAnalyzer()
        self.direction = DirectionAnalyzer()

        self.confidence = ConfidenceCalibrator(
            expected_domain_count=len(
                EXPECTED_DOMAINS
            )
        )

        self.forecast = ForecastFusion()

    @staticmethod
    def _normalize(
        assessments: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in assessments
            if isinstance(item, dict)
        ]

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 85:
            return "Critical"

        if score >= 70:
            return "High"

        if score >= 55:
            return "Elevated"

        if score >= 35:
            return "Guarded"

        return "Low"

    @staticmethod
    def _analytical_status(
        score: float,
    ) -> str:
        if score >= 85:
            return "critical"

        if score >= 70:
            return "alert"

        if score >= 55:
            return "warning"

        if score >= 35:
            return "watch"

        return "nominal"

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

    @staticmethod
    def _direction_for(
        assessment: dict[str, Any],
    ) -> str:
        explicit = str(
            assessment.get("direction")
            or ""
        ).strip().lower()

        if explicit in {
            "deteriorating",
            "improving",
            "stable",
        }:
            return explicit

        forecast = (
            assessment.get("forecast")
            or assessment.get(
                "forecast_probabilities"
            )
            or {}
        )

        if not isinstance(forecast, dict):
            return "unknown"

        values: list[float] = []

        for value in forecast.values():
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue

        if len(values) < 2:
            return "unknown"

        delta = values[-1] - values[0]

        if delta >= 3:
            return "deteriorating"

        if delta <= -3:
            return "improving"

        return "stable"

    @staticmethod
    def _aggregate_evidence(
        assessments: list[dict[str, Any]],
    ) -> dict[str, int]:
        totals = {
            "live_signals": 0,
            "recent_indicators": 0,
            "structural_indicators": 0,
            "unknown_evidence": 0,
            "total_evidence": 0,
        }

        for assessment in assessments:
            composition = (
                assessment.get(
                    "evidence_composition"
                )
                or {}
            )

            if not isinstance(
                composition,
                dict,
            ):
                continue

            for key in totals:
                try:
                    totals[key] += int(
                        composition.get(key, 0)
                        or 0
                    )
                except (TypeError, ValueError):
                    continue

        return totals

    @staticmethod
    def _collect_key_drivers(
        assessments: list[dict[str, Any]],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        drivers: list[dict[str, Any]] = []

        for assessment in assessments:
            domain = SIAMFusionEngine._domain_key(
                assessment
            )

            items = (
                assessment.get("key_drivers")
                or []
            )

            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                row = dict(item)
                row.setdefault(
                    "domain",
                    domain,
                )
                drivers.append(row)

        def rank(
            item: dict[str, Any],
        ) -> tuple[float, float]:
            try:
                severity = float(
                    item.get("severity") or 0
                )
            except (TypeError, ValueError):
                severity = 0.0

            try:
                confidence = float(
                    item.get("confidence") or 0
                )
            except (TypeError, ValueError):
                confidence = 0.0

            return severity, confidence

        return sorted(
            drivers,
            key=rank,
            reverse=True,
        )[:limit]

    @staticmethod
    def _collect_strings(
        assessments: list[dict[str, Any]],
        key: str,
        limit: int,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for assessment in assessments:
            values = assessment.get(key) or []

            if not isinstance(values, list):
                continue

            for value in values:
                text = str(value).strip()

                if (
                    not text
                    or text.lower() in seen
                ):
                    continue

                seen.add(text.lower())
                output.append(text)

                if len(output) >= limit:
                    return output

        return output

    @staticmethod
    def _build_watch_indicators(
        assessments: list[dict[str, Any]],
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        seen: set[str] = set()

        for assessment in assessments:
            domain = SIAMFusionEngine._domain_key(
                assessment
            )

            indicators = (
                assessment.get("indicators")
                or []
            )

            if not isinstance(
                indicators,
                list,
            ):
                continue

            for indicator in indicators:
                if not isinstance(
                    indicator,
                    dict,
                ):
                    continue

                name = str(
                    indicator.get("name")
                    or ""
                ).strip()

                if not name:
                    continue

                identity = (
                    f"{domain}:{name}"
                ).lower()

                if identity in seen:
                    continue

                seen.add(identity)

                row = dict(indicator)
                row.setdefault(
                    "domain",
                    domain,
                )

                output.append(row)

                if len(output) >= limit:
                    return output

        return output

    def fuse(
        self,
        *,
        region: str,
        assessments: Iterable[
            dict[str, Any]
        ],
    ) -> StrategicIntelligence:
        items = self._normalize(
            assessments
        )

        if not items:
            raise ValueError(
                "SIAM fusion requires at least "
                "one authoritative domain assessment."
            )

        # Normalize direction once so every downstream
        # analytical component receives the same trajectory.
        normalized_items: list[
            dict[str, Any]
        ] = []

        for item in items:
            row = dict(item)

            if not row.get("direction"):
                row["direction"] = (
                    self._direction_for(row)
                )

            normalized_items.append(row)

        dominant_result = (
            self.dominant.analyze(
                normalized_items
            )
        )

        convergence_result = (
            self.convergence.analyze(
                normalized_items
            )
        )

        contradiction_result = (
            self.contradiction.analyze(
                normalized_items
            )
        )

        direction_result = (
            self.direction.analyze(
                normalized_items
            )
        )

        confidence_result = (
            self.confidence.calibrate(
                normalized_items,
                convergence_score=(
                    convergence_result
                    .convergence_score
                ),
                contradiction_score=(
                    contradiction_result
                    .contradiction_score
                ),
            )
        )

        forecast_result = (
            self.forecast.fuse(
                normalized_items
            )
        )

        # SIAM preserves the leading deterministic domain
        # risk as the executive risk anchor.
        risk_score = round(
            dominant_result.leading_risk_score,
            2,
        )

        risk_level = self._risk_level(
            risk_score
        )

        confidence = round(
            confidence_result
            .calibrated_confidence,
            2,
        )

        available_domains = {
            self._domain_key(item)
            for item in normalized_items
        }

        missing_domains = [
            domain
            for domain in EXPECTED_DOMAINS
            if domain not in available_domains
        ]

        leading_label = (
            dominant_result
            .leading_domain_label
            or dominant_result
            .leading_domain
            or "Unknown"
        )

        supporting = (
            dominant_result
            .supporting_domains
        )

        if supporting:
            support_text = (
                ", ".join(supporting)
            )
            executive_judgment = (
                f"{leading_label} is the "
                f"leading regional risk domain, "
                f"reinforced by {support_text}. "
                f"The overall strategic trajectory "
                f"is {direction_result.strategic_direction}."
            )
        else:
            executive_judgment = (
                f"{leading_label} is the "
                f"leading regional risk domain. "
                f"The overall strategic trajectory "
                f"is {direction_result.strategic_direction}."
            )

        bluf = (
            f"{region} is assessed at "
            f"{risk_level.lower()} strategic risk "
            f"({risk_score:.1f}/100), led by "
            f"{leading_label}, with a "
            f"{direction_result.strategic_direction} "
            f"trajectory."
        )

        cross_domain_dynamics = [
            {
                "type": "reinforcing_pair",
                **pair,
            }
            for pair in (
                convergence_result
                .reinforcing_pairs
            )
        ]

        convergence_findings = list(
            convergence_result.findings
        )

        contradictions = list(
            contradiction_result
            .contradictions
        )

        implications = (
            self._collect_strings(
                normalized_items,
                "implications",
                10,
            )
        )

        recommendations = (
            self._collect_strings(
                normalized_items,
                "recommendations",
                10,
            )
        )

        intelligence_gaps = (
            self._collect_strings(
                normalized_items,
                "intelligence_gaps",
                10,
            )
        )

        if missing_domains:
            intelligence_gaps.append(
                "Missing authoritative domain "
                "coverage: "
                + ", ".join(
                    missing_domains
                )
                + "."
            )

        confidence_breakdown = {
            "calibrated_confidence": (
                confidence_result
                .calibrated_confidence
            ),
            "average_domain_confidence": (
                confidence_result
                .average_domain_confidence
            ),
            "coverage_factor": (
                confidence_result
                .coverage_factor
            ),
            "freshness_factor": (
                confidence_result
                .freshness_factor
            ),
            "agreement_factor": (
                confidence_result
                .agreement_factor
            ),
            "penalties": (
                confidence_result.penalties
            ),
            "rationale": (
                confidence_result.rationale
            ),
        }

        return StrategicIntelligence(
            region=region,
            title=(
                f"{region} Strategic Intelligence"
            ),
            bluf=bluf,
            executive_judgment=(
                executive_judgment
            ),
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
            analytical_status=(
                self._analytical_status(
                    risk_score
                )
            ),
            leading_domain=(
                dominant_result.leading_domain
            ),
            strategic_direction=(
                direction_result
                .strategic_direction
            ),
            domain_assessments=(
                normalized_items
            ),
            key_drivers=(
                self._collect_key_drivers(
                    normalized_items
                )
            ),
            cross_domain_dynamics=(
                cross_domain_dynamics
            ),
            convergence_findings=(
                convergence_findings
            ),
            contradictions=contradictions,
            forecast_probabilities=(
                forecast_result
                .fused_forecast
            ),
            implications=implications,
            recommended_actions=(
                recommendations
            ),
            intelligence_gaps=(
                intelligence_gaps
            ),
            watch_indicators=(
                self._build_watch_indicators(
                    normalized_items
                )
            ),
            coverage={
                "expected_domains": len(
                    EXPECTED_DOMAINS
                ),
                "available_domains": len(
                    available_domains
                ),
                "missing_domains": (
                    missing_domains
                ),
                "supporting_domains": (
                    supporting
                ),
                "ranked_domains": (
                    dominant_result
                    .ranked_domains
                ),
            },
            evidence_composition=(
                self._aggregate_evidence(
                    normalized_items
                )
            ),
            provenance={
                "engine": "SIAMFusionEngine",
                "method": (
                    "deterministic-cross-domain-fusion"
                ),
                "dominant": asdict(
                    dominant_result
                ),
                "convergence": asdict(
                    convergence_result
                ),
                "contradiction": asdict(
                    contradiction_result
                ),
                "direction": asdict(
                    direction_result
                ),
                "confidence": (
                    confidence_breakdown
                ),
                "forecast": asdict(
                    forecast_result
                ),
            },
        )


siam_fusion_engine = SIAMFusionEngine()
