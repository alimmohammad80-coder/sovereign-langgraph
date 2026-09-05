from datetime import datetime, timezone

from app.cyber_information.confidence import assess_confidence
from app.cyber_information.hybrid_fusion import HybridFusionEngine
from app.cyber_information.models import EvidenceStatus
from app.cyber_information.phase5_models import HybridFusionRequest, HybridSignal, HybridSignalDomain


def _confidence(score_hint: float = 0.8):
    return assess_confidence(
        evidence_quality=score_hint,
        source_diversity=0.8,
        corroboration=0.8,
        analytic_uncertainty=0.2,
        rationale="synthetic test confidence",
    )


def test_single_signal_does_not_create_high_hybrid_score():
    engine = HybridFusionEngine()
    request = HybridFusionRequest(
        title="isolated signal",
        external_signals=[
            HybridSignal(
                domain=HybridSignalDomain.CYBER,
                title="Isolated scan",
                summary="Synthetic isolated cyber signal",
                countries=["TWN"],
                targets=["telecom"],
                severity_score=60,
                confidence=_confidence(),
                evidence_status=EvidenceStatus.OBSERVED,
            )
        ],
    )
    result = engine.assess(request)
    assert result.signal_count == 1
    assert result.cross_domain_convergence.score == 20
    assert result.hybrid_score < 40


def test_cross_domain_convergence_increases_with_shared_context():
    engine = HybridFusionEngine()
    t = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    shared = dict(countries=["TWN"], targets=["telecom"], actors=["Actor X"], occurred_at=t, confidence=_confidence())
    request = HybridFusionRequest(
        title="Synthetic hybrid activity",
        external_signals=[
            HybridSignal(domain=HybridSignalDomain.CYBER, title="Cyber intrusion", summary="Synthetic", severity_score=80, **shared),
            HybridSignal(domain=HybridSignalDomain.INFORMATION, title="Narrative amplification", summary="Synthetic", severity_score=75, **shared),
            HybridSignal(domain=HybridSignalDomain.MILITARY, title="Military activity", summary="Synthetic", severity_score=85, **shared),
            HybridSignal(domain=HybridSignalDomain.INFRASTRUCTURE, title="Infrastructure targeting", summary="Synthetic", sectors=["telecommunications"], severity_score=82, **shared),
        ],
    )
    result = engine.assess(request)
    assert len(result.domains_present) == 4
    assert result.temporal_convergence.score >= 90
    assert result.target_convergence.score > 50
    assert result.actor_convergence.score > 50
    assert result.geographic_convergence.score > 50
    assert result.hybrid_score >= 70


def test_assessment_preserves_no_proof_of_orchestration_language():
    result = HybridFusionEngine().assess(HybridFusionRequest(title="empty"))
    assert "not proof of orchestration" in result.summary.lower()
    assert result.metadata["formula_version"] == "hybrid-fusion-v1"
