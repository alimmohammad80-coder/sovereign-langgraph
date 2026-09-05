from datetime import datetime, timedelta, timezone

from app.cyber_information.information_engine import (
    analyze_information_environment,
    assess_coordination,
    assess_propagation,
    cluster_observations,
    lexical_similarity,
    trace_evolution,
)
from app.cyber_information.phase4_models import InformationObservation


def _obs(text: str, hours: int, domain: str, account: str | None = None) -> InformationObservation:
    return InformationObservation(
        text=text,
        title=text[:50],
        source="test",
        source_domain=domain,
        author_or_account=account,
        published_at=datetime(2026, 9, 4, 12, tzinfo=timezone.utc) + timedelta(hours=hours),
        countries=["TWN"],
    )


def test_lexical_similarity_is_deterministic():
    a = "Foreign sanctions caused severe domestic food shortages"
    b = "Domestic food shortages were caused by foreign sanctions"
    c = "A tropical storm crossed the coastline overnight"
    assert lexical_similarity(a, b) > lexical_similarity(a, c)
    assert lexical_similarity(a, b) == lexical_similarity(a, b)


def test_narrative_clustering_groups_similar_observations():
    observations = [
        _obs("Foreign sanctions caused domestic food shortages", 0, "alpha.test"),
        _obs("Domestic food shortages caused by foreign sanctions", 1, "beta.test"),
        _obs("Major earthquake damages regional roads", 2, "gamma.test"),
    ]
    clusters = cluster_observations(observations, threshold=0.4)
    assert len(clusters) == 2
    assert max(cluster.observation_count for cluster in clusters) == 2


def test_propagation_and_coordination_are_separate_assessments():
    observations = [
        _obs("Foreign sanctions caused domestic food shortages", 0, "alpha.test", "acct1"),
        _obs("Domestic food shortages caused by foreign sanctions", 0, "beta.test", "acct1"),
        _obs("Foreign sanctions are causing domestic food shortages", 1, "gamma.test", "acct2"),
    ]
    cluster = cluster_observations(observations, threshold=0.35)[0]
    propagation = assess_propagation(cluster, observations)
    coordination = assess_coordination(cluster, observations)
    assert propagation.propagation_score >= 0
    assert coordination.coordination_score >= 0
    assert coordination.evidence_status.value == "inferred"
    assert any("not proof" in caveat.lower() for caveat in coordination.caveats)


def test_narrative_evolution_tracks_mutation():
    observations = [
        _obs("Foreign sanctions caused domestic food shortages", 0, "alpha.test"),
        _obs("Foreign sanctions caused domestic food shortages and energy rationing", 1, "beta.test"),
    ]
    cluster = cluster_observations(observations, threshold=0.3)[0]
    evolution = trace_evolution(cluster, observations)
    assert len(evolution.points) == 2
    assert evolution.points[0].mutation_score == 0
    assert evolution.points[1].mutation_score >= 0


def test_end_to_end_information_environment_analysis():
    records = [
        {"source": "gdelt", "record_type": "information_environment_observation", "title": "Foreign sanctions caused domestic food shortages", "domain": "alpha.test", "seen_date": "20260904T120000Z", "countries": ["TWN"]},
        {"source": "gdelt", "record_type": "information_environment_observation", "title": "Domestic food shortages caused by foreign sanctions", "domain": "beta.test", "seen_date": "20260904T130000Z", "countries": ["TWN"]},
    ]
    result = analyze_information_environment(records, threshold=0.35)
    assert result["observation_count"] == 2
    assert result["cluster_count"] == 1
    product = result["products"][0]
    assert "campaign" in product
    assert "coordination" in product
    assert product["campaign"]["evidence_status"] == "assessed"
