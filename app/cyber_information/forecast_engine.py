from __future__ import annotations

import math
from statistics import mean

from .confidence import assess_confidence
from .models import CrossModuleDestination
from .phase5_models import HybridCampaignAssessment, HybridSignal
from .phase6_models import (
    CyberHybridForecast,
    EarlyWarningLevel,
    ForecastBand,
    ForecastHorizon,
    ForecastRequest,
)


class CyberHybridForecastEngine:
    """Deterministic probabilistic baseline for Phase 6.

    This is a versioned, auditable logistic baseline. It is intentionally simple
    enough to inspect and later calibrate on historical labeled episodes.
    """

    HORIZON_MULTIPLIERS = {
        ForecastHorizon.DAYS_7: 0.72,
        ForecastHorizon.DAYS_30: 1.00,
        ForecastHorizon.DAYS_90: 1.18,
    }

    def forecast(self, request: ForecastRequest) -> CyberHybridForecast:
        assessment = request.assessment
        recent_signals = request.recent_signals

        signal_momentum = self._signal_momentum(recent_signals)
        severity = self._mean_signal_severity(recent_signals)
        breadth = min(1.0, len(assessment.domains_present) / 6.0)
        hybrid = assessment.hybrid_score / 100.0
        temporal = assessment.temporal_convergence.score / 100.0
        target = assessment.target_convergence.score / 100.0
        infrastructure = assessment.infrastructure_relevance.score / 100.0
        confidence_score = assessment.confidence.score

        base_logit = self._logit(request.prior_escalation_rate)
        escalation_linear = (
            base_logit
            + 1.25 * (hybrid - 0.5)
            + 0.65 * (temporal - 0.5)
            + 0.55 * (target - 0.5)
            + 0.45 * (infrastructure - 0.5)
            + 0.50 * (breadth - 0.5)
            + 0.45 * (signal_momentum - 0.5)
            + 0.35 * (severity - 0.5)
        )

        persistence_linear = (
            self._logit(request.prior_persistence_rate)
            + 1.00 * (hybrid - 0.5)
            + 0.55 * (breadth - 0.5)
            + 0.55 * (signal_momentum - 0.5)
            + 0.30 * (confidence_score - 0.5)
        )

        escalation = [
            self._band(
                horizon=horizon,
                probability=self._sigmoid(escalation_linear * multiplier),
                assessment=assessment,
                recent_signals=recent_signals,
                drivers=self._escalation_drivers(assessment, signal_momentum, severity),
                indicators=self._watch_indicators(assessment),
            )
            for horizon, multiplier in self.HORIZON_MULTIPLIERS.items()
        ]

        persistence = [
            self._band(
                horizon=horizon,
                probability=self._sigmoid(persistence_linear * multiplier),
                assessment=assessment,
                recent_signals=recent_signals,
                drivers=self._persistence_drivers(assessment, signal_momentum),
                indicators=self._watch_indicators(assessment),
            )
            for horizon, multiplier in self.HORIZON_MULTIPLIERS.items()
        ]

        p30 = next(b.probability for b in escalation if b.horizon == ForecastHorizon.DAYS_30)
        warning_score = round(
            100
            * (
                0.55 * p30
                + 0.20 * hybrid
                + 0.10 * infrastructure
                + 0.10 * signal_momentum
                + 0.05 * breadth
            ),
            1,
        )

        return CyberHybridForecast(
            title=assessment.title,
            escalation=escalation,
            persistence=persistence,
            warning_score=warning_score,
            warning_level=self._warning_level(warning_score),
            destinations=[
                CrossModuleDestination.STRATEGIC_EARLY_WARNING,
                CrossModuleDestination.CONFLICT_FORECASTING,
                CrossModuleDestination.COUNTRY_INTELLIGENCE,
                CrossModuleDestination.GLOBAL_RISK_MAP,
                CrossModuleDestination.INTELLIGENCE_STREAM,
                CrossModuleDestination.STRATEGIC_AI_AGENTS,
            ],
            supporting_signal_ids=[signal.id for signal in recent_signals],
            rationale=self._forecast_rationale(assessment, signal_momentum, severity, breadth),
            metadata={
                "hybrid_score": assessment.hybrid_score,
                "signal_momentum": round(signal_momentum, 4),
                "mean_signal_severity": round(severity, 4),
                "domain_breadth": round(breadth, 4),
                "prior_escalation_rate": request.prior_escalation_rate,
                "prior_persistence_rate": request.prior_persistence_rate,
                "calibration_status": "baseline_requires_historical_calibration",
            },
        )

    def to_early_warning_handoff(self, forecast: CyberHybridForecast) -> dict:
        return {
            "schema_version": "cyber-hybrid-early-warning-handoff-v1",
            "source_module": "cyber_information_operations",
            "warning_score": forecast.warning_score,
            "warning_level": forecast.warning_level.value,
            "forecast": {
                "escalation": {b.horizon.value: b.model_dump(mode="json") for b in forecast.escalation},
                "persistence": {b.horizon.value: b.model_dump(mode="json") for b in forecast.persistence},
            },
            "destinations": [d.value for d in forecast.destinations],
            "formula_version": forecast.formula_version,
            "evidence_status": forecast.evidence_status.value,
            "rationale": forecast.rationale,
        }

    @staticmethod
    def _sigmoid(value: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, value))))

    @staticmethod
    def _logit(probability: float) -> float:
        p = max(0.001, min(0.999, probability))
        return math.log(p / (1.0 - p))

    @staticmethod
    def _signal_momentum(signals: list[HybridSignal]) -> float:
        if not signals:
            return 0.25
        recent_weights = []
        for signal in signals:
            score = signal.severity_score / 100.0
            if signal.domain.value in {"cyber", "information", "military", "infrastructure"}:
                score += 0.08
            recent_weights.append(min(1.0, score))
        return min(1.0, mean(recent_weights) * min(1.35, 0.75 + 0.08 * len(signals)))

    @staticmethod
    def _mean_signal_severity(signals: list[HybridSignal]) -> float:
        if not signals:
            return 0.35
        return mean(signal.severity_score for signal in signals) / 100.0

    def _band(
        self,
        *,
        horizon: ForecastHorizon,
        probability: float,
        assessment: HybridCampaignAssessment,
        recent_signals: list[HybridSignal],
        drivers: list[str],
        indicators: list[str],
    ) -> ForecastBand:
        source_diversity = min(1.0, len(assessment.domains_present) / 5.0)
        corroboration = min(1.0, 0.4 + 0.07 * assessment.signal_count)
        evidence_quality = min(1.0, 0.55 + 0.4 * assessment.confidence.score)
        uncertainty = max(0.10, 0.52 - 0.25 * source_diversity - 0.18 * corroboration)
        confidence = assess_confidence(
            evidence_quality=evidence_quality,
            source_diversity=source_diversity,
            corroboration=corroboration,
            analytic_uncertainty=uncertainty,
            rationale="Forecast confidence reflects cross-domain breadth, corroboration, and Phase 5 assessment confidence.",
        )
        half_width = max(0.06, 0.26 - 0.16 * confidence.score)
        return ForecastBand(
            horizon=horizon,
            probability=round(probability, 4),
            lower_bound=round(max(0.0, probability - half_width), 4),
            upper_bound=round(min(1.0, probability + half_width), 4),
            confidence=confidence,
            drivers=drivers,
            indicators_to_watch=indicators,
        )

    @staticmethod
    def _escalation_drivers(assessment: HybridCampaignAssessment, momentum: float, severity: float) -> list[str]:
        drivers = []
        for label, dimension in [
            ("temporal convergence", assessment.temporal_convergence),
            ("target convergence", assessment.target_convergence),
            ("cross-domain convergence", assessment.cross_domain_convergence),
            ("infrastructure relevance", assessment.infrastructure_relevance),
        ]:
            if dimension.score >= 65:
                drivers.append(f"Elevated {label} ({dimension.score:.0f}/100)")
        if momentum >= 0.65:
            drivers.append("Recent signal momentum is elevated")
        if severity >= 0.70:
            drivers.append("Recent signal severity is high")
        return drivers or ["Current evidence does not show a dominant escalation driver"]

    @staticmethod
    def _persistence_drivers(assessment: HybridCampaignAssessment, momentum: float) -> list[str]:
        drivers = [f"Activity spans {len(assessment.domains_present)} domains"]
        if assessment.hybrid_score >= 65:
            drivers.append("Hybrid convergence is sustained across multiple dimensions")
        if momentum >= 0.60:
            drivers.append("Recent activity indicates continuing operational momentum")
        return drivers

    @staticmethod
    def _watch_indicators(assessment: HybridCampaignAssessment) -> list[str]:
        indicators = [
            "New cyber exploitation or intrusion activity",
            "Acceleration in narrative propagation or coordinated amplification",
            "Expansion into additional critical-infrastructure sectors",
            "Military or diplomatic activity temporally aligned with cyber/information signals",
        ]
        if assessment.targets:
            indicators.append(f"Repeated activity against tracked targets: {', '.join(assessment.targets[:3])}")
        return indicators

    @staticmethod
    def _forecast_rationale(assessment: HybridCampaignAssessment, momentum: float, severity: float, breadth: float) -> list[str]:
        return [
            f"Hybrid campaign score contributes as an observed convergence prior: {assessment.hybrid_score:.1f}/100.",
            f"Recent signal momentum: {momentum:.2f}; mean recent severity: {severity:.2f}.",
            f"Cross-domain breadth factor: {breadth:.2f} across {len(assessment.domains_present)} domains.",
            "Probabilities are generated by a versioned logistic baseline and must be historically calibrated before being presented as fully calibrated operational forecasts.",
        ]

    @staticmethod
    def _warning_level(score: float) -> EarlyWarningLevel:
        if score >= 85:
            return EarlyWarningLevel.CRITICAL
        if score >= 70:
            return EarlyWarningLevel.HIGH
        if score >= 55:
            return EarlyWarningLevel.WARNING
        if score >= 35:
            return EarlyWarningLevel.WATCH
        return EarlyWarningLevel.ROUTINE
