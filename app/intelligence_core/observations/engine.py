from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.intelligence_core.indicators.mapping_engine import (
    IndicatorMappingEngine,
)
from app.intelligence_core.materiality.scoring import (
    MaterialityScorer,
)
from app.intelligence_core.observations.schemas import (
    IntelligenceObservation,
    ObservationDirection,
    ObservationEntity,
)
from app.normalization.canonical_record import (
    CanonicalIntelligenceRecord,
)


class ObservationEngine:
    def __init__(
        self,
        *,
        indicator_mapper: IndicatorMappingEngine | None = None,
        materiality_scorer: type[MaterialityScorer] = (
            MaterialityScorer
        ),
    ) -> None:
        self.indicator_mapper = (
            indicator_mapper or IndicatorMappingEngine()
        )
        self.materiality_scorer = materiality_scorer

    def create_observation(
        self,
        record: CanonicalIntelligenceRecord,
    ) -> IntelligenceObservation:
        indicator_impacts = self.indicator_mapper.map_record(record)

        cross_module_relevance = min(
            1.0,
            0.35 + (0.15 * len(indicator_impacts)),
        )

        novelty = self._extract_novelty(record)

        materiality = self.materiality_scorer.calculate(
            severity=record.severity,
            confidence=record.confidence,
            source_reliability=record.source_reliability,
            novelty=novelty,
            cross_module_relevance=cross_module_relevance,
        )

        effective_at = (
            record.observed_at
            or record.published_at
            or datetime.now(timezone.utc)
        )

        return IntelligenceObservation(
            observation_key=self._build_observation_key(record),
            title=record.title,
            summary=record.summary,
            observation_type=(
                record.event_type
                or record.record_type
                or "GENERAL_OBSERVATION"
            ),
            source_key=record.source_key,
            source_record_id=record.source_record_id,
            evidence_id=record.evidence_id,
            canonical_record_id=record.record_id,
            country_iso3=record.location.country_iso3,
            region_key=record.location.region_key,
            direction=self._normalize_direction(record.direction),
            severity=record.severity,
            confidence=record.confidence,
            source_reliability=record.source_reliability,
            novelty=novelty,
            materiality_score=materiality.score,
            materiality_level=materiality.level,
            is_material=materiality.is_material,
            entities=[
                ObservationEntity(
                    entity_type=entity.entity_type,
                    name=entity.name,
                    canonical_name=entity.canonical_name,
                    external_id=entity.external_id,
                    country_iso3=entity.country_iso3,
                    confidence=entity.confidence,
                    metadata=entity.metadata,
                )
                for entity in record.entities
            ],
            indicator_impacts=indicator_impacts,
            effective_at=effective_at,
            metadata={
                "themes": record.themes,
                "sectors": record.sectors,
                "commodities": record.commodities,
                "canonical_url": record.canonical_url,
                "materiality_components": materiality.components,
                "normalization_metadata": record.metadata,
            },
        )

    def create_many(
        self,
        records: list[CanonicalIntelligenceRecord],
    ) -> tuple[
        list[IntelligenceObservation],
        list[dict[str, str | int]],
    ]:
        observations: list[IntelligenceObservation] = []
        errors: list[dict[str, str | int]] = []

        for index, record in enumerate(records):
            try:
                observations.append(
                    self.create_observation(record)
                )
            except Exception as exc:
                errors.append(
                    {
                        "index": index,
                        "record_id": record.record_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )

        return observations, errors

    @staticmethod
    def _build_observation_key(
        record: CanonicalIntelligenceRecord,
    ) -> str:
        identity = "|".join(
            [
                record.source_key,
                record.source_record_id or record.record_id,
                record.event_type or record.record_type,
                record.location.country_iso3 or "GLOBAL",
            ]
        )

        digest = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()[:20]

        return f"OBS-{record.source_key}-{digest}".upper()

    @staticmethod
    def _extract_novelty(
        record: CanonicalIntelligenceRecord,
    ) -> float:
        raw_value = record.metadata.get("novelty", 0.65)

        try:
            novelty = float(raw_value)
        except (TypeError, ValueError):
            novelty = 0.65

        if novelty > 1:
            novelty /= 100

        return max(0.0, min(1.0, novelty))

    @staticmethod
    def _normalize_direction(
        direction: str,
    ) -> ObservationDirection:
        normalized = str(direction).strip().upper()

        try:
            return ObservationDirection(normalized)
        except ValueError:
            return ObservationDirection.UNKNOWN
