from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from statistics import mean

from .confidence import assess_confidence
from .models import EvidenceStatus
from .phase5_models import (
    FusionDimension,
    HybridCampaignAssessment,
    HybridFusionRequest,
    HybridSignal,
    HybridSignalDomain,
)


class HybridFusionEngine:
    """Deterministic, explainable hybrid-threat fusion.

    This engine assesses convergence; it does not infer intent or attribution
    beyond what is explicitly present in source objects.
    """

    def signals_from_request(self, request: HybridFusionRequest) -> list[HybridSignal]:
        signals: list[HybridSignal] = list(request.external_signals)

        for incident in request.cyber_incidents:
            signals.append(HybridSignal(
                domain=HybridSignalDomain.CYBER,
                title=incident.title,
                summary=incident.summary,
                occurred_at=incident.occurred_at,
                observed_at=incident.observed_at,
                countries=incident.countries,
                sectors=incident.sectors,
                actors=incident.suspected_actors,
                targets=incident.target_names,
                severity_score=incident.severity_score,
                confidence=incident.confidence,
                evidence_status=incident.evidence_status,
                source_ids=[str(incident.id)],
                metadata={"campaign_names": incident.campaign_names, "cves": incident.cves},
            ))

        for campaign in request.information_campaigns:
            signals.append(HybridSignal(
                domain=HybridSignalDomain.INFORMATION,
                title=campaign.name,
                summary=campaign.summary,
                occurred_at=campaign.first_observed_at,
                countries=campaign.countries,
                actors=campaign.suspected_actors,
                targets=campaign.target_audiences,
                severity_score=campaign.strategic_relevance_score,
                confidence=campaign.confidence,
                evidence_status=campaign.evidence_status,
                source_ids=[str(campaign.id)],
                metadata={"coordination_score": campaign.coordination_score, "narrative_ids": [str(x) for x in campaign.narrative_ids]},
            ))

        for observation in request.information_observations:
            signals.append(HybridSignal(
                domain=HybridSignalDomain.INFORMATION,
                title=observation.title or observation.text[:120],
                summary=observation.text,
                occurred_at=observation.published_at,
                observed_at=observation.observed_at,
                countries=observation.countries,
                severity_score=observation.strategic_relevance_score,
                confidence=observation.confidence,
                evidence_status=observation.evidence_status,
                source_ids=[str(observation.id)],
                metadata={"platform": observation.platform, "source": observation.source},
            ))

        for profile in request.infrastructure_profiles:
            signals.append(HybridSignal(
                domain=HybridSignalDomain.INFRASTRUCTURE,
                title=f"Infrastructure exposure: {profile.name}",
                summary=f"{profile.name} targeting/exposure profile for {profile.sector}",
                countries=[profile.country_iso3] if profile.country_iso3 else [],
                sectors=[profile.sector],
                actors=profile.actor_names,
                targets=[profile.name],
                severity_score=profile.targeting_score,
                confidence=profile.confidence,
                evidence_status=EvidenceStatus.ASSESSED,
                source_ids=[profile.name],
                metadata={"criticality_score": profile.criticality_score, "vulnerability_ids": profile.vulnerability_ids},
            ))

        return signals

    @staticmethod
    def _temporal_dimension(signals: list[HybridSignal]) -> FusionDimension:
        times = [s.occurred_at or s.observed_at for s in signals]
        if len(times) < 2:
            return FusionDimension(score=0, rationale=["Fewer than two time-stamped signals."])
        span_hours = (max(times) - min(times)).total_seconds() / 3600
        if span_hours <= 6:
            score = 95
        elif span_hours <= 24:
            score = 85
        elif span_hours <= 72:
            score = 70
        elif span_hours <= 168:
            score = 50
        else:
            score = 25
        return FusionDimension(score=score, rationale=[f"Signal span is {span_hours:.1f} hours across {len(times)} observations."])

    @staticmethod
    def _overlap_dimension(values: list[list[str]], label: str) -> FusionDimension:
        flattened = [v.strip().lower() for group in values for v in group if v and v.strip()]
        if not flattened:
            return FusionDimension(score=0, rationale=[f"No {label} values available."])
        counts = Counter(flattened)
        shared = {k: v for k, v in counts.items() if v >= 2}
        repeated = sum(shared.values())
        score = min(100.0, 25.0 + (repeated / max(1, len(flattened))) * 75.0) if shared else 20.0
        rationale = [f"{len(shared)} repeated {label} values across {len(flattened)} total references."]
        if shared:
            rationale.append("Shared: " + ", ".join(sorted(shared)[:8]))
        return FusionDimension(score=round(score, 1), rationale=rationale)

    @staticmethod
    def _cross_domain_dimension(signals: list[HybridSignal]) -> FusionDimension:
        domains = sorted(set(s.domain for s in signals), key=lambda x: x.value)
        count = len(domains)
        score = {0: 0, 1: 20, 2: 55, 3: 75, 4: 88}.get(count, 95)
        return FusionDimension(score=score, rationale=[f"{count} distinct domains present: {', '.join(d.value for d in domains) or 'none'}."])

    @staticmethod
    def _infrastructure_dimension(signals: list[HybridSignal]) -> FusionDimension:
        infra = [s for s in signals if s.domain in {HybridSignalDomain.INFRASTRUCTURE, HybridSignalDomain.SUPPLY_CHAIN}]
        cyber_targets = [s for s in signals if s.domain == HybridSignalDomain.CYBER and s.targets]
        if not infra and not cyber_targets:
            return FusionDimension(score=0, rationale=["No infrastructure or supply-chain targeting signal present."])
        avg = mean([s.severity_score for s in infra + cyber_targets])
        score = min(100.0, 0.7 * avg + 10 * min(3, len(infra + cyber_targets)))
        return FusionDimension(score=round(score, 1), rationale=[f"{len(infra)} infrastructure/supply-chain signals and {len(cyber_targets)} cyber targeting signals."])

    def assess(self, request: HybridFusionRequest) -> HybridCampaignAssessment:
        signals = self.signals_from_request(request)
        temporal = self._temporal_dimension(signals)
        targets = self._overlap_dimension([s.targets for s in signals], "target")
        actors = self._overlap_dimension([s.actors for s in signals], "actor")
        geography = self._overlap_dimension([s.countries for s in signals], "country")
        cross_domain = self._cross_domain_dimension(signals)
        infrastructure = self._infrastructure_dimension(signals)

        hybrid_score = round(
            0.20 * temporal.score
            + 0.20 * targets.score
            + 0.15 * actors.score
            + 0.15 * geography.score
            + 0.20 * cross_domain.score
            + 0.10 * infrastructure.score,
            1,
        )

        confidences = [s.confidence.score for s in signals]
        evidence_quality = mean(confidences) if confidences else 0.2
        source_diversity = min(1.0, len({sid for s in signals for sid in s.source_ids}) / 5.0) if signals else 0.0
        corroboration = min(1.0, (targets.score + actors.score + geography.score) / 300.0)
        uncertainty = max(0.05, 1.0 - min(1.0, len(signals) / 8.0))
        confidence = assess_confidence(
            evidence_quality=evidence_quality,
            source_diversity=source_diversity,
            corroboration=corroboration,
            analytic_uncertainty=uncertainty,
            rationale="Confidence reflects source confidence, diversity, cross-signal corroboration, and observation volume; it does not assert common control or intent.",
        )

        countries = sorted({c for s in signals for c in s.countries})
        sectors = sorted({c for s in signals for c in s.sectors})
        actor_names = sorted({c for s in signals for c in s.actors})
        target_names = sorted({c for s in signals for c in s.targets})
        domains = sorted(set(s.domain for s in signals), key=lambda x: x.value)

        summary = (
            f"{len(signals)} signals across {len(domains)} domains produce a hybrid convergence score of {hybrid_score:.1f}/100. "
            "This is an analytic convergence assessment, not proof of orchestration, attribution, or hostile intent."
        )

        return HybridCampaignAssessment(
            title=request.title,
            summary=summary,
            countries=countries,
            sectors=sectors,
            actors=actor_names,
            targets=target_names,
            signal_count=len(signals),
            domains_present=domains,
            temporal_convergence=temporal,
            target_convergence=targets,
            actor_convergence=actors,
            geographic_convergence=geography,
            cross_domain_convergence=cross_domain,
            infrastructure_relevance=infrastructure,
            hybrid_score=hybrid_score,
            confidence=confidence,
            supporting_signal_ids=[s.id for s in signals],
            metadata={
                "formula_version": "hybrid-fusion-v1",
                "weights": {
                    "temporal": 0.20,
                    "target": 0.20,
                    "actor": 0.15,
                    "geography": 0.15,
                    "cross_domain": 0.20,
                    "infrastructure": 0.10,
                },
            },
        )
