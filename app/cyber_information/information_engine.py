from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

from .confidence import assess_confidence
from .models import EvidenceStatus, SourceProvenance
from .phase4_models import (
    CoordinationAssessment,
    CoordinationLevel,
    InformationCampaign,
    InformationObservation,
    NarrativeCluster,
    NarrativeEvolution,
    NarrativeEvolutionPoint,
    NarrativeStatus,
    PropagationAssessment,
)


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "will",
    "with", "its", "their", "they", "them", "about", "after", "before", "over", "under",
}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[\w'-]+", text.lower(), flags=re.UNICODE)
    return [word for word in words if len(word) > 2 and word not in _STOPWORDS]


def lexical_similarity(a: str, b: str) -> float:
    """Cosine similarity over deterministic token-frequency vectors."""
    ca, cb = Counter(_tokens(a)), Counter(_tokens(b))
    if not ca or not cb:
        return 0.0
    common = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in ca.values()))
    norm_b = math.sqrt(sum(v * v for v in cb.values()))
    if not norm_a or not norm_b:
        return 0.0
    return round(dot / (norm_a * norm_b), 4)


def observation_from_record(record: dict) -> InformationObservation:
    provenance = []
    if p := record.get("provenance"):
        provenance.append(SourceProvenance(**p))
    text = record.get("description") or record.get("title") or record.get("text") or ""
    return InformationObservation(
        text=text,
        title=record.get("title"),
        source=record.get("source", "unknown"),
        source_record_id=record.get("source_record_id"),
        source_domain=record.get("domain"),
        source_country=record.get("source_country"),
        language=record.get("language"),
        platform=record.get("platform"),
        author_or_account=record.get("author_or_account"),
        published_at=_parse_datetime(record.get("seen_date") or record.get("published")),
        url=record.get("url"),
        countries=record.get("countries") or [],
        entities=record.get("entities") or [],
        metadata={"record_type": record.get("record_type")},
        provenance=provenance,
    )


def cluster_observations(
    observations: list[InformationObservation], *, threshold: float = 0.45
) -> list[NarrativeCluster]:
    """Greedy, deterministic clustering using representative-text similarity."""
    groups: list[list[InformationObservation]] = []
    similarities: list[list[float]] = []
    for observation in sorted(observations, key=lambda x: x.published_at or x.observed_at):
        best_idx, best_score = None, 0.0
        for idx, group in enumerate(groups):
            score = lexical_similarity(observation.text, group[0].text)
            if score > best_score:
                best_idx, best_score = idx, score
        if best_idx is not None and best_score >= threshold:
            groups[best_idx].append(observation)
            similarities[best_idx].append(best_score)
        else:
            groups.append([observation])
            similarities.append([1.0])

    clusters: list[NarrativeCluster] = []
    for group, scores in zip(groups, similarities):
        times = [o.published_at or o.observed_at for o in group]
        domains = sorted({o.source_domain for o in group if o.source_domain})
        countries = sorted({c for o in group for c in o.countries})
        platforms = sorted({o.platform for o in group if o.platform})
        avg_similarity = round(sum(scores) / len(scores), 4)
        elapsed = max((max(times) - min(times)).total_seconds() / 3600, 0.01)
        velocity = min(100.0, round((len(group) / max(elapsed, 1.0)) * 20.0, 2))
        reach = min(100.0, round(len(domains) * 12 + len(countries) * 10 + len(platforms) * 10, 2))
        confidence = assess_confidence(
            evidence_quality=0.8,
            source_diversity=min(1.0, max(0.2, len(domains) / 5)),
            corroboration=min(1.0, avg_similarity),
            analytic_uncertainty=max(0.05, 1.0 - avg_similarity),
            rationale="Deterministic narrative grouping based on token-frequency similarity and observed source diversity.",
        )
        status = NarrativeStatus.ACCELERATING if velocity >= 65 else NarrativeStatus.ACTIVE
        label = group[0].title or " ".join(_tokens(group[0].text)[:8]) or "Unlabeled narrative"
        clusters.append(NarrativeCluster(
            label=label[:180], representative_text=group[0].text,
            observation_ids=[o.id for o in group], observation_count=len(group),
            first_observed_at=min(times), last_observed_at=max(times), status=status,
            similarity_threshold=threshold, average_similarity=avg_similarity,
            countries=countries, source_domains=domains, platforms=platforms,
            velocity_score=velocity, reach_score=reach,
            strategic_relevance_score=min(100.0, round(0.55 * velocity + 0.45 * reach, 2)),
            confidence=confidence,
        ))
    return clusters


def assess_propagation(cluster: NarrativeCluster, observations: list[InformationObservation]) -> PropagationAssessment:
    members = [o for o in observations if o.id in set(cluster.observation_ids)]
    times = [o.published_at or o.observed_at for o in members]
    elapsed = max((max(times) - min(times)).total_seconds() / 3600, 0.0) if len(times) > 1 else 0.0
    sources = {o.source_domain or o.source for o in members}
    countries = {c for o in members for c in o.countries}
    platforms = {o.platform for o in members if o.platform}
    velocity = min(100.0, (len(members) / max(elapsed, 1.0)) * 20.0)
    reach = min(100.0, len(sources) * 12 + len(countries) * 10 + len(platforms) * 10)
    cross_platform = min(100.0, len(platforms) * 25.0)
    score = round(0.45 * velocity + 0.4 * reach + 0.15 * cross_platform, 2)
    return PropagationAssessment(
        cluster_id=cluster.id, observation_count=len(members), distinct_sources=len(sources),
        distinct_countries=len(countries), distinct_platforms=len(platforms), elapsed_hours=round(elapsed, 2),
        velocity_score=round(velocity, 2), reach_score=round(reach, 2),
        cross_platform_score=round(cross_platform, 2), propagation_score=score,
        rationale=["Velocity reflects observations per elapsed hour.", "Reach reflects distinct sources, countries, and platforms."],
    )


def assess_coordination(cluster: NarrativeCluster, observations: list[InformationObservation]) -> CoordinationAssessment:
    members = [o for o in observations if o.id in set(cluster.observation_ids)]
    if not members:
        members = []
    times = sorted(o.published_at or o.observed_at for o in members)
    elapsed = (times[-1] - times[0]).total_seconds() / 3600 if len(times) > 1 else 24.0
    temporal = min(100.0, (len(members) / max(elapsed, 1.0)) * 25.0)
    text_score = cluster.average_similarity * 100
    domains = {o.source_domain or o.source for o in members}
    diversity = min(100.0, len(domains) * 20.0)
    accounts = [o.author_or_account for o in members if o.author_or_account]
    duplicate_accounts = len(accounts) - len(set(accounts))
    account_reuse = min(100.0, duplicate_accounts * 25.0)
    score = round(0.35 * temporal + 0.35 * text_score + 0.15 * diversity + 0.15 * account_reuse, 2)
    level = CoordinationLevel.VERY_HIGH if score >= 80 else CoordinationLevel.HIGH if score >= 65 else CoordinationLevel.MODERATE if score >= 40 else CoordinationLevel.LOW
    confidence = assess_confidence(
        evidence_quality=0.72,
        source_diversity=min(1.0, max(0.2, len(domains) / 5)),
        corroboration=min(1.0, cluster.average_similarity),
        analytic_uncertainty=0.35 if accounts else 0.5,
        rationale="Coordination is inferred from temporal synchrony, textual similarity, source diversity, and observed account reuse; it does not establish common control or attribution.",
    )
    indicators = []
    if temporal >= 60: indicators.append("high_temporal_synchrony")
    if text_score >= 70: indicators.append("high_textual_similarity")
    if diversity >= 60: indicators.append("multi_source_amplification")
    if account_reuse > 0: indicators.append("account_reuse_observed")
    return CoordinationAssessment(
        cluster_id=cluster.id, coordination_score=score, coordination_level=level,
        temporal_synchrony_score=round(temporal, 2), text_similarity_score=round(text_score, 2),
        source_diversity_score=round(diversity, 2), account_reuse_score=round(account_reuse, 2),
        confidence=confidence, indicators=indicators,
        caveats=["Coordination indicators are not proof of orchestration.", "No actor attribution is inferred from coordination score alone."],
    )


def trace_evolution(cluster: NarrativeCluster, observations: list[InformationObservation]) -> NarrativeEvolution:
    members = sorted(
        [o for o in observations if o.id in set(cluster.observation_ids)],
        key=lambda o: o.published_at or o.observed_at,
    )
    if not members:
        return NarrativeEvolution(cluster_id=cluster.id, origin_text=cluster.representative_text)
    origin = members[0].text
    points = []
    for obs in members:
        sim = lexical_similarity(origin, obs.text)
        points.append(NarrativeEvolutionPoint(
            observed_at=obs.published_at or obs.observed_at, text=obs.text, source=obs.source,
            source_domain=obs.source_domain, lexical_similarity_to_origin=sim,
            mutation_score=round((1 - sim) * 100, 2),
        ))
    max_mutation = max((p.mutation_score for p in points), default=0.0)
    return NarrativeEvolution(
        cluster_id=cluster.id, origin_text=origin, points=points,
        mutation_count=sum(1 for p in points[1:] if p.mutation_score >= 30),
        max_mutation_score=max_mutation,
        evolution_direction="diversifying" if max_mutation >= 45 else "stable",
    )


def build_campaign(cluster: NarrativeCluster, propagation: PropagationAssessment, coordination: CoordinationAssessment) -> InformationCampaign:
    manipulation = round(min(100.0, 0.55 * coordination.coordination_score + 0.25 * propagation.propagation_score + 0.20 * cluster.strategic_relevance_score), 2)
    confidence = assess_confidence(
        evidence_quality=0.75,
        source_diversity=min(1.0, max(0.2, len(cluster.source_domains) / 5)),
        corroboration=min(1.0, cluster.average_similarity),
        analytic_uncertainty=0.35,
        rationale="Campaign assessment combines observed narrative propagation with inferred coordination indicators; manipulation likelihood is not equivalent to falsity or actor attribution.",
    )
    return InformationCampaign(
        name=f"Narrative campaign: {cluster.label}"[:220], narrative_cluster_ids=[cluster.id],
        status=cluster.status, first_observed_at=cluster.first_observed_at, last_observed_at=cluster.last_observed_at,
        countries=cluster.countries, source_domains=cluster.source_domains, platforms=cluster.platforms,
        propagation_score=propagation.propagation_score, coordination_score=coordination.coordination_score,
        strategic_relevance_score=cluster.strategic_relevance_score,
        manipulation_likelihood_score=manipulation, evidence_status=EvidenceStatus.ASSESSED,
        confidence=confidence,
        analytic_judgments=[
            "Narrative activity is grouped by observable textual similarity.",
            "Coordination indicators may reflect common events or copying and do not independently establish orchestration.",
        ],
    )


def analyze_information_environment(records: list[dict], *, threshold: float = 0.45) -> dict:
    observations = [observation_from_record(record) for record in records if (record.get("description") or record.get("title") or record.get("text"))]
    clusters = cluster_observations(observations, threshold=threshold)
    products = []
    for cluster in clusters:
        propagation = assess_propagation(cluster, observations)
        coordination = assess_coordination(cluster, observations)
        evolution = trace_evolution(cluster, observations)
        campaign = build_campaign(cluster, propagation, coordination)
        products.append({
            "cluster": cluster.model_dump(mode="json"),
            "propagation": propagation.model_dump(mode="json"),
            "coordination": coordination.model_dump(mode="json"),
            "evolution": evolution.model_dump(mode="json"),
            "campaign": campaign.model_dump(mode="json"),
        })
    return {"observation_count": len(observations), "cluster_count": len(clusters), "products": products}


def _parse_datetime(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    for fmt in ("%Y%m%dT%H%M%SZ", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None
