from __future__ import annotations

from dataclasses import dataclass, field

from app.intelligence_core.observations.schemas import (
    IndicatorImpact,
)
from app.normalization.canonical_record import (
    CanonicalIntelligenceRecord,
)


@dataclass(frozen=True, slots=True)
class IndicatorMappingRule:
    rule_key: str
    indicator_key: str
    event_types: frozenset[str] = field(default_factory=frozenset)
    themes: frozenset[str] = field(default_factory=frozenset)
    sectors: frozenset[str] = field(default_factory=frozenset)
    base_impact: float = 0.0
    confidence_multiplier: float = 1.0
    rationale: str | None = None


DEFAULT_RULES = [
    IndicatorMappingRule(
        rule_key="MILITARY_ACTIVITY_TO_POSTURE",
        indicator_key="MILITARY_POSTURE",
        event_types=frozenset(
            {
                "MILITARY_ACTIVITY",
                "TROOP_MOVEMENT",
                "NAVAL_ACTIVITY",
                "MOBILIZATION",
            }
        ),
        themes=frozenset(
            {
                "MILITARY POSTURE",
                "MILITARY ACTIVITY",
            }
        ),
        base_impact=18.0,
        rationale="Military activity affects force posture.",
    ),
    IndicatorMappingRule(
        rule_key="MARITIME_ACTIVITY_TO_SECURITY",
        indicator_key="MARITIME_SECURITY",
        event_types=frozenset(
            {
                "MILITARY_ACTIVITY",
                "NAVAL_ACTIVITY",
                "MARITIME_INCIDENT",
            }
        ),
        themes=frozenset(
            {
                "MARITIME SECURITY",
                "SHIPPING SECURITY",
            }
        ),
        sectors=frozenset({"SHIPPING"}),
        base_impact=16.0,
        rationale="Maritime activity affects shipping security.",
    ),
    IndicatorMappingRule(
        rule_key="MARITIME_ACTIVITY_TO_ENERGY",
        indicator_key="ENERGY_SECURITY",
        themes=frozenset(
            {
                "ENERGY SECURITY",
                "MARITIME SECURITY",
            }
        ),
        sectors=frozenset({"ENERGY"}),
        base_impact=12.0,
        rationale=(
            "Maritime disruption near energy corridors affects "
            "energy security."
        ),
    ),
    IndicatorMappingRule(
        rule_key="SANCTIONS_TO_ECONOMIC_PRESSURE",
        indicator_key="SANCTIONS_PRESSURE",
        event_types=frozenset(
            {
                "SANCTIONS",
                "SANCTIONS_DESIGNATION",
                "EXPORT_CONTROL",
            }
        ),
        themes=frozenset({"SANCTIONS", "EXPORT CONTROLS"}),
        base_impact=20.0,
        rationale="Sanctions activity raises economic pressure.",
    ),
    IndicatorMappingRule(
        rule_key="CONFLICT_TO_ESCALATION",
        indicator_key="CONFLICT_ESCALATION",
        event_types=frozenset(
            {
                "ARMED_CONFLICT",
                "MILITARY_ACTIVITY",
                "MISSILE_LAUNCH",
                "AIRSTRIKE",
                "MOBILIZATION",
            }
        ),
        themes=frozenset(
            {
                "CONFLICT",
                "ESCALATION",
                "MILITARY POSTURE",
            }
        ),
        base_impact=22.0,
        rationale="Conflict activity affects escalation risk.",
    ),
]


class IndicatorMappingEngine:
    def __init__(
        self,
        rules: list[IndicatorMappingRule] | None = None,
    ) -> None:
        self._rules = rules or list(DEFAULT_RULES)

    def map_record(
        self,
        record: CanonicalIntelligenceRecord,
    ) -> list[IndicatorImpact]:
        event_type = (record.event_type or "").strip().upper()
        themes = {item.strip().upper() for item in record.themes}
        sectors = {item.strip().upper() for item in record.sectors}

        impacts: list[IndicatorImpact] = []

        for rule in self._rules:
            matches = self._matching_dimensions(
                rule=rule,
                event_type=event_type,
                themes=themes,
                sectors=sectors,
            )

            if not matches:
                continue

            direction_multiplier = self._direction_multiplier(
                record.direction
            )

            severity_multiplier = max(
                0.25,
                record.severity / 100.0,
            )

            impact = (
                rule.base_impact
                * severity_multiplier
                * direction_multiplier
            )

            mapping_confidence = min(
                1.0,
                record.confidence
                * rule.confidence_multiplier
                * min(1.0, 0.65 + 0.15 * len(matches)),
            )

            impacts.append(
                IndicatorImpact(
                    indicator_key=rule.indicator_key,
                    impact_score=round(impact, 2),
                    confidence=round(mapping_confidence, 3),
                    mapping_rule=rule.rule_key,
                    rationale=rule.rationale,
                    metadata={
                        "matched_dimensions": sorted(matches),
                    },
                )
            )

        return self._combine_duplicate_indicators(impacts)

    @staticmethod
    def _matching_dimensions(
        *,
        rule: IndicatorMappingRule,
        event_type: str,
        themes: set[str],
        sectors: set[str],
    ) -> set[str]:
        matches: set[str] = set()

        if event_type and event_type in rule.event_types:
            matches.add("event_type")

        if themes.intersection(rule.themes):
            matches.add("themes")

        if sectors.intersection(rule.sectors):
            matches.add("sectors")

        return matches

    @staticmethod
    def _direction_multiplier(direction: str) -> float:
        normalized = str(direction).strip().upper()

        if normalized == "INCREASING":
            return 1.0
        if normalized == "DECREASING":
            return -1.0
        if normalized == "MIXED":
            return 0.35
        if normalized == "STABLE":
            return 0.15

        return 0.25

    @staticmethod
    def _combine_duplicate_indicators(
        impacts: list[IndicatorImpact],
    ) -> list[IndicatorImpact]:
        combined: dict[str, IndicatorImpact] = {}

        for impact in impacts:
            existing = combined.get(impact.indicator_key)

            if existing is None:
                combined[impact.indicator_key] = impact
                continue

            total_impact = max(
                -100.0,
                min(
                    100.0,
                    existing.impact_score + impact.impact_score,
                ),
            )

            combined[impact.indicator_key] = IndicatorImpact(
                indicator_key=impact.indicator_key,
                impact_score=round(total_impact, 2),
                confidence=max(
                    existing.confidence,
                    impact.confidence,
                ),
                mapping_rule=(
                    f"{existing.mapping_rule}+{impact.mapping_rule}"
                ),
                rationale=existing.rationale or impact.rationale,
                metadata={
                    "combined": True,
                    "rules": [
                        existing.mapping_rule,
                        impact.mapping_rule,
                    ],
                },
            )

        return sorted(
            combined.values(),
            key=lambda item: abs(item.impact_score),
            reverse=True,
        )
