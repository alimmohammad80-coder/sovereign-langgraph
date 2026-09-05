from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .phase7_models import (
    DeliveryResult,
    DeliveryState,
    DestinationPayload,
    IntegrationDestination,
    IntegrationPlan,
    PlatformIntelligenceEnvelope,
)


class CrossModuleIntegrationBus:
    """Build destination-specific platform handoffs without coupling to module internals.

    This layer plans and serializes cross-module deliveries. Actual persistence or
    destination-specific transport can be bound later without changing the contract.
    """

    MATERIALITY_THRESHOLDS = {
        IntegrationDestination.STRATEGIC_EARLY_WARNING: 55,
        IntegrationDestination.CONFLICT_FORECASTING: 60,
        IntegrationDestination.COUNTRY_INTELLIGENCE: 45,
        IntegrationDestination.GLOBAL_RISK_MAP: 50,
        IntegrationDestination.INTELLIGENCE_STREAM: 35,
        IntegrationDestination.STRATEGIC_AI_AGENTS: 50,
        IntegrationDestination.SUPPLY_CHAIN_INTELLIGENCE: 55,
        IntegrationDestination.CORPORATE_FINANCIAL_RISK: 55,
    }

    def make_envelope(self, source: dict[str, Any]) -> PlatformIntelligenceEnvelope:
        source_object_type = str(source.get("source_object_type") or source.get("schema_version") or "unknown")
        source_object_id = str(source.get("id") or source.get("event_id") or source.get("source_object_id") or "unknown")
        countries = sorted(set(source.get("countries") or []))
        sectors = sorted(set(source.get("sectors") or []))
        actors = sorted(set(source.get("actors") or source.get("suspected_actors") or []))
        targets = sorted(set(source.get("targets") or source.get("target_names") or []))
        severity = float(source.get("warning_score", source.get("hybrid_score", source.get("severity_score", 50))))
        confidence = source.get("confidence")
        if confidence is None:
            raise ValueError("source object requires confidence")
        evidence_status = source.get("evidence_status", "assessed")
        p30 = source.get("forecast_probability_30d")
        if p30 is None:
            horizons = source.get("escalation_forecast") or source.get("horizons") or []
            for item in horizons:
                if str(item.get("horizon")) in {"30d", "30"}:
                    p30 = item.get("probability")
                    break
        material = {
            "type": source_object_type,
            "id": source_object_id,
            "countries": countries,
            "sectors": sectors,
            "severity": round(severity, 2),
            "warning_level": source.get("warning_level"),
        }
        dedup = hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()
        return PlatformIntelligenceEnvelope(
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            title=str(source.get("title") or "Cyber & Information Operations assessment"),
            summary=str(source.get("summary") or "Cross-module cyber and information intelligence handoff."),
            countries=countries,
            sectors=sectors,
            actors=actors,
            targets=targets,
            severity_score=max(0, min(100, severity)),
            confidence=confidence,
            evidence_status=evidence_status,
            forecast_probability_30d=p30,
            warning_level=source.get("warning_level"),
            model_version=source.get("model_version") or source.get("formula_version"),
            calibration_status=source.get("calibration_status"),
            deduplication_key=dedup,
            metadata=source.get("metadata") or {},
        )

    def materiality_score(self, envelope: PlatformIntelligenceEnvelope, destination: IntegrationDestination) -> float:
        score = envelope.severity_score
        if envelope.forecast_probability_30d is not None:
            score = 0.7 * score + 0.3 * (envelope.forecast_probability_30d * 100)
        if destination == IntegrationDestination.CONFLICT_FORECASTING and not envelope.countries:
            score -= 20
        if destination == IntegrationDestination.SUPPLY_CHAIN_INTELLIGENCE and not envelope.sectors:
            score -= 20
        if destination == IntegrationDestination.CORPORATE_FINANCIAL_RISK and not envelope.targets:
            score -= 20
        return round(max(0, min(100, score)), 2)

    def destination_payload(self, envelope: PlatformIntelligenceEnvelope, destination: IntegrationDestination) -> DestinationPayload:
        materiality = self.materiality_score(envelope, destination)
        threshold = self.MATERIALITY_THRESHOLDS[destination]
        ready = materiality >= threshold
        state = DeliveryState.READY if ready else DeliveryState.SUPPRESSED
        reason = f"materiality {materiality} {'meets' if ready else 'below'} threshold {threshold}"
        common = {
            "source_module": envelope.source_module,
            "source_object_type": envelope.source_object_type,
            "source_object_id": envelope.source_object_id,
            "title": envelope.title,
            "summary": envelope.summary,
            "countries": envelope.countries,
            "sectors": envelope.sectors,
            "actors": envelope.actors,
            "targets": envelope.targets,
            "severity_score": envelope.severity_score,
            "confidence": envelope.confidence.model_dump(mode="json"),
            "evidence_status": envelope.evidence_status.value,
            "forecast_probability_30d": envelope.forecast_probability_30d,
            "warning_level": envelope.warning_level,
            "model_version": envelope.model_version,
            "calibration_status": envelope.calibration_status,
            "deduplication_key": envelope.deduplication_key,
        }
        if destination == IntegrationDestination.STRATEGIC_EARLY_WARNING:
            common.update({"signal_type": "cyber_information_hybrid_warning", "warning_score": materiality})
        elif destination == IntegrationDestination.CONFLICT_FORECASTING:
            common.update({"driver_type": "cyber_information_escalation", "driver_score": materiality})
        elif destination == IntegrationDestination.COUNTRY_INTELLIGENCE:
            common.update({"indicator_family": "cyber_information_operations", "indicator_score": materiality})
        elif destination == IntegrationDestination.GLOBAL_RISK_MAP:
            common.update({"risk_layer": "cyber_information", "risk_score": materiality})
        elif destination == IntegrationDestination.INTELLIGENCE_STREAM:
            common.update({"stream_type": "material_intelligence_update", "priority_score": materiality})
        elif destination == IntegrationDestination.STRATEGIC_AI_AGENTS:
            common.update({"agent_signal_type": "material_change", "relevance_score": materiality})
        elif destination == IntegrationDestination.SUPPLY_CHAIN_INTELLIGENCE:
            common.update({"risk_driver": "cyber_infrastructure_disruption", "disruption_score": materiality})
        elif destination == IntegrationDestination.CORPORATE_FINANCIAL_RISK:
            common.update({"risk_driver": "cyber_information_exposure", "exposure_score": materiality})
        return DestinationPayload(destination=destination, state=state, reason=reason, materiality_score=materiality, payload=common)

    def plan(self, source: dict[str, Any], destinations: list[IntegrationDestination] | None = None) -> IntegrationPlan:
        envelope = self.make_envelope(source)
        targets = destinations or list(IntegrationDestination)
        routes = [self.destination_payload(envelope, d) for d in targets]
        return IntegrationPlan(
            envelope=envelope,
            routes=routes,
            suppressed_count=sum(1 for r in routes if r.state == DeliveryState.SUPPRESSED),
            ready_count=sum(1 for r in routes if r.state == DeliveryState.READY),
        )

    def mark_delivered(self, route: DestinationPayload, deduplication_key: str) -> DeliveryResult:
        if route.state != DeliveryState.READY:
            return DeliveryResult(destination=route.destination, state=DeliveryState.SUPPRESSED, deduplication_key=deduplication_key)
        return DeliveryResult(
            destination=route.destination,
            state=DeliveryState.DELIVERED,
            deduplication_key=deduplication_key,
            delivered_at=datetime.now(timezone.utc),
            response_metadata={"transport": "adapter_contract", "persisted": False},
        )
