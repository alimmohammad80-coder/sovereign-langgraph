from app.cyber_information.confidence import assess_confidence
from app.cyber_information.forecast_engine import CyberHybridForecastEngine
from app.cyber_information.models import EvidenceStatus
from app.cyber_information.phase5_models import (
    FusionDimension,
    HybridCampaignAssessment,
    HybridSignal,
    HybridSignalDomain,
)
from app.cyber_information.phase6_models import ForecastRequest


def confidence(score=0.82):
    return assess_confidence(
        evidence_quality=score,
        source_diversity=0.8,
        corroboration=0.85,
        analytic_uncertainty=0.15,
        rationale="synthetic test",
    )


def assessment(score=78):
    dim = FusionDimension(score=80, rationale=["synthetic"])
    return HybridCampaignAssessment(
        title="Synthetic hybrid campaign",
        summary="Test campaign",
        countries=["TWN"],
        sectors=["telecommunications", "energy"],
        actors=["Synthetic Actor"],
        targets=["Critical infrastructure"],
        signal_count=6,
        domains_present=[
            HybridSignalDomain.CYBER,
            HybridSignalDomain.INFORMATION,
            HybridSignalDomain.MILITARY,
            HybridSignalDomain.INFRASTRUCTURE,
        ],
        temporal_convergence=dim,
        target_convergence=dim,
        actor_convergence=FusionDimension(score=65, rationale=[]),
        geographic_convergence=dim,
        cross_domain_convergence=FusionDimension(score=90, rationale=[]),
        infrastructure_relevance=FusionDimension(score=85, rationale=[]),
        hybrid_score=score,
        confidence=confidence(),
        evidence_status=EvidenceStatus.ASSESSED,
    )


def signals():
    return [
        HybridSignal(
            domain=domain,
            title=f"Synthetic {domain.value}",
            summary="Synthetic signal",
            countries=["TWN"],
            sectors=["telecommunications"],
            targets=["Critical infrastructure"],
            severity_score=82,
            confidence=confidence(),
        )
        for domain in [
            HybridSignalDomain.CYBER,
            HybridSignalDomain.INFORMATION,
            HybridSignalDomain.MILITARY,
            HybridSignalDomain.INFRASTRUCTURE,
        ]
    ]


def test_high_convergence_produces_material_warning():
    result = CyberHybridForecastEngine().forecast(
        ForecastRequest(assessment=assessment(), recent_signals=signals())
    )
    assert result.warning_score >= 35
    assert len(result.escalation) == 3
    assert all(b.lower_bound <= b.probability <= b.upper_bound for b in result.escalation)
    assert result.metadata["calibration_status"] == "baseline_requires_historical_calibration"


def test_sparse_evidence_remains_restrained():
    low = assessment(score=20)
    low.signal_count = 1
    low.domains_present = [HybridSignalDomain.CYBER]
    low.temporal_convergence = FusionDimension(score=20, rationale=[])
    low.target_convergence = FusionDimension(score=15, rationale=[])
    low.cross_domain_convergence = FusionDimension(score=10, rationale=[])
    low.infrastructure_relevance = FusionDimension(score=20, rationale=[])
    result = CyberHybridForecastEngine().forecast(ForecastRequest(assessment=low, recent_signals=[]))
    p30 = next(b.probability for b in result.escalation if b.horizon.value == "30d")
    assert p30 < 0.5
    assert result.warning_score < 55


def test_early_warning_handoff_is_explicit():
    engine = CyberHybridForecastEngine()
    result = engine.forecast(ForecastRequest(assessment=assessment(), recent_signals=signals()))
    handoff = engine.to_early_warning_handoff(result)
    assert handoff["source_module"] == "cyber_information_operations"
    assert handoff["formula_version"] == "cyber-hybrid-logit-v1"
    assert "strategic_early_warning" in handoff["destinations"]
    assert "conflict_forecasting" in handoff["destinations"]
