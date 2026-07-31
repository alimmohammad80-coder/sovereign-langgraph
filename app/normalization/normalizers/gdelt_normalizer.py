from __future__ import annotations

from datetime import datetime
from typing import Any

from app.normalization.base_normalizer import BaseNormalizer
from app.normalization.canonical_record import (
    CanonicalEntity,
    CanonicalIntelligenceRecord,
    CanonicalLocation,
)


class GDELTNormalizer(BaseNormalizer):
    source_key = "GDELT"

    def normalize(
        self,
        raw_record: dict[str, Any],
    ) -> CanonicalIntelligenceRecord:
        title = (
            raw_record.get("title")
            or raw_record.get("name")
            or "Untitled GDELT record"
        )

        raw_text = (
            raw_record.get("raw_text")
            or raw_record.get("content")
            or raw_record.get("summary")
            or title
        )

        country_iso3 = (
            raw_record.get("country_iso3")
            or raw_record.get("actor1_country_code")
            or raw_record.get("action_geo_country_code")
        )

        entities = self._extract_entities(raw_record)

        return CanonicalIntelligenceRecord(
            source_key=self.source_key,
            source_record_id=(
                raw_record.get("source_external_id")
                or raw_record.get("globaleventid")
                or raw_record.get("url")
            ),
            evidence_id=raw_record.get("evidence_id"),
            record_type="EVENT",
            event_type=(
                raw_record.get("event_type")
                or raw_record.get("event_code")
                or "GENERAL_EVENT"
            ),
            title=title,
            summary=raw_record.get("summary") or raw_text[:500],
            raw_text=raw_text,
            published_at=self._parse_datetime(
                raw_record.get("published_at")
                or raw_record.get("dateadded")
                or raw_record.get("seendate")
            ),
            observed_at=(
                self._parse_datetime(raw_record.get("observed_at"))
                or datetime.now().astimezone()
            ),
            language_code=raw_record.get(
                "language_code",
                "en",
            ),
            location=CanonicalLocation(
                country_iso3=country_iso3,
                region_key=raw_record.get("region_key"),
                place_name=(
                    raw_record.get("location_name")
                    or raw_record.get("action_geo_fullname")
                ),
                latitude=self._to_float(
                    raw_record.get("latitude")
                    or raw_record.get("action_geo_lat")
                ),
                longitude=self._to_float(
                    raw_record.get("longitude")
                    or raw_record.get("action_geo_long")
                ),
            ),
            entities=entities,
            themes=self._as_list(raw_record.get("themes")),
            sectors=self._as_list(raw_record.get("sectors")),
            commodities=self._as_list(
                raw_record.get("commodities")
            ),
            direction=raw_record.get("direction", "STABLE"),
            severity=self._clamp(
                raw_record.get("severity", 0),
                0,
                100,
            ),
            confidence=self._normalize_ratio(
                raw_record.get("confidence", 0.65)
            ),
            source_reliability=self._normalize_ratio(
                raw_record.get("source_reliability", 0.75)
            ),
            canonical_url=(
                raw_record.get("canonical_url")
                or raw_record.get("url")
            ),
            metadata={
                "tone": raw_record.get("tone"),
                "goldstein_scale": raw_record.get(
                    "goldstein_scale"
                ),
                "actor1_name": raw_record.get("actor1_name"),
                "actor2_name": raw_record.get("actor2_name"),
                "original": raw_record.get("metadata", {}),
            },
        )

    def _extract_entities(
        self,
        raw_record: dict[str, Any],
    ) -> list[CanonicalEntity]:
        candidates = [
            (
                "ACTOR",
                raw_record.get("actor1_name"),
                raw_record.get("actor1_country_code"),
            ),
            (
                "ACTOR",
                raw_record.get("actor2_name"),
                raw_record.get("actor2_country_code"),
            ),
            (
                "LOCATION",
                raw_record.get("location_name")
                or raw_record.get("action_geo_fullname"),
                raw_record.get("country_iso3")
                or raw_record.get("action_geo_country_code"),
            ),
        ]

        entities: list[CanonicalEntity] = []
        seen: set[tuple[str, str]] = set()

        for entity_type, name, country_iso3 in candidates:
            if not name:
                continue

            key = (entity_type, str(name).casefold())

            if key in seen:
                continue

            seen.add(key)

            entities.append(
                CanonicalEntity(
                    entity_type=entity_type,
                    name=str(name),
                    country_iso3=country_iso3,
                    confidence=0.75,
                )
            )

        return entities

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            return value

        text = str(value).strip()

        formats = (
            "%Y%m%d%H%M%S",
            "%Y%m%d",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
        )

        for date_format in formats:
            try:
                return datetime.strptime(text, date_format)
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )
        except ValueError:
            return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_list(value: Any) -> list[str]:
        if value is None:
            return []

        if isinstance(value, list):
            return [str(item).strip() for item in value if item]

        if isinstance(value, str):
            separator = ";" if ";" in value else ","

            return [
                item.strip()
                for item in value.split(separator)
                if item.strip()
            ]

        return [str(value)]

    @staticmethod
    def _clamp(
        value: Any,
        minimum: float,
        maximum: float,
    ) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = minimum

        return max(minimum, min(maximum, number))

    @staticmethod
    def _normalize_ratio(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.5

        if number > 1:
            number /= 100

        return max(0.0, min(1.0, number))
