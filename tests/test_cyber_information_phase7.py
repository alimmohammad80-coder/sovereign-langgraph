from app.cyber_information.confidence import assess_confidence
from app.cyber_information.integration_bus import CrossModuleIntegrationBus
from app.cyber_information.phase7_models import DeliveryState, IntegrationDestination


def _source(severity: float = 82, p30: float = 0.68) -> dict:
    return {
        "source_object_type": "cyber-hybrid-forecast-v1",
        "source_object_id": "forecast-001",
        "title": "Synthetic hybrid warning",
        "summary": "Synthetic cross-module integration test.",
        "countries": ["TWN"],
        "sectors": ["telecommunications", "energy"],
        "actors": ["Example Actor"],
        "targets": ["Example Telecom"],
        "warning_score": severity,
        "forecast_probability_30d": p30,
        "warning_level": "high",
        "model_version": "cyber-hybrid-logit-v1",
        "calibration_status": "baseline_requires_historical_calibration",
        "evidence_status": "assessed",
        "confidence": assess_confidence(
            evidence_quality=0.85,
            source_diversity=0.8,
            corroboration=0.8,
            analytic_uncertainty=0.2,
            rationale="synthetic test",
        ).model_dump(mode="json"),
    }


def test_high_materiality_routes_to_core_modules():
    bus = CrossModuleIntegrationBus()
    plan = bus.plan(_source())
    ready = {r.destination for r in plan.routes if r.state == DeliveryState.READY}
    assert IntegrationDestination.STRATEGIC_EARLY_WARNING in ready
    assert IntegrationDestination.COUNTRY_INTELLIGENCE in ready
    assert IntegrationDestination.GLOBAL_RISK_MAP in ready
    assert IntegrationDestination.INTELLIGENCE_STREAM in ready
    assert plan.ready_count > 0


def test_sparse_supply_chain_context_is_penalized():
    bus = CrossModuleIntegrationBus()
    source = _source(severity=56, p30=0.4)
    source["sectors"] = []
    plan = bus.plan(source, destinations=[IntegrationDestination.SUPPLY_CHAIN_INTELLIGENCE])
    assert plan.routes[0].state == DeliveryState.SUPPRESSED


def test_deduplication_key_is_stable_for_same_material_object():
    bus = CrossModuleIntegrationBus()
    one = bus.make_envelope(_source())
    two = bus.make_envelope(_source())
    assert one.deduplication_key == two.deduplication_key


def test_destination_payloads_are_semantically_specific():
    bus = CrossModuleIntegrationBus()
    envelope = bus.make_envelope(_source())
    sews = bus.destination_payload(envelope, IntegrationDestination.STRATEGIC_EARLY_WARNING)
    conflict = bus.destination_payload(envelope, IntegrationDestination.CONFLICT_FORECASTING)
    assert sews.payload["signal_type"] == "cyber_information_hybrid_warning"
    assert conflict.payload["driver_type"] == "cyber_information_escalation"


def test_simulated_delivery_does_not_claim_persistence():
    bus = CrossModuleIntegrationBus()
    plan = bus.plan(_source(), destinations=[IntegrationDestination.INTELLIGENCE_STREAM])
    result = bus.mark_delivered(plan.routes[0], plan.envelope.deduplication_key)
    assert result.state == DeliveryState.DELIVERED
    assert result.response_metadata["persisted"] is False
