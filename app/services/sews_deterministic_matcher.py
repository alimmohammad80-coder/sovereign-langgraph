from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9]{3,}")


@dataclass(slots=True)
class IndicatorMatch:
    indicator_key: str
    score: float
    matched_terms: list[str]
    polarity: str
    score_breakdown: dict[str, float] = field(default_factory=dict)


class SEWSDeterministicIndicatorMatcher:
    STOPWORDS = {
        "the", "and", "for", "with", "from", "that", "this",
        "warning", "indicator", "strategic", "risk", "activity",
        "event", "events", "evidence", "current", "change",
        "changes", "system", "monitoring", "assess", "assessment",
        "relevant", "related", "source", "sources", "energy",
        "security", "supply", "chain", "conflict", "military",
        "economic", "financial", "political", "humanitarian",
        "public", "health", "operations", "domain", "regional",
        "global", "report", "reports", "news",
    }

    CLASS_POLARITY = {
        "PRECURSOR": "SUPPORTING",
        "ACCELERANT": "SUPPORTING",
        "TRIGGER": "SUPPORTING",
        "CONTRA": "CONTRADICTING",
    }

    @classmethod
    def _terms(cls, *values: Any) -> set[str]:
        output: set[str] = set()

        for value in values:
            if value is None:
                continue

            if isinstance(value, (list, tuple, set)):
                output |= cls._terms(*value)
                continue

            if isinstance(value, dict):
                output |= cls._terms(
                    *value.keys(),
                    *value.values(),
                )
                continue

            normalized = str(value).lower().replace("_", " ")

            output |= {
                token
                for token in TOKEN_RE.findall(normalized)
                if token not in cls.STOPWORDS
            }

        return output

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        try:
            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            return None

    def _freshness_score(self, evidence: dict[str, Any]) -> float:
        timestamp = self._parse_datetime(
            evidence.get("observed_at")
            or evidence.get("published_at")
            or evidence.get("collected_at")
        )

        if timestamp is None:
            return 0.45

        age_hours = max(
            0.0,
            (
                datetime.now(timezone.utc)
                - timestamp.astimezone(timezone.utc)
            ).total_seconds()
            / 3600,
        )

        # Smooth decay: ~0.75 at 72 hours, ~0.50 at 7 days.
        return round(
            math.exp(-age_hours / (24 * 10)),
            6,
        )

    def _source_reliability(
        self,
        evidence: dict[str, Any],
    ) -> float:
        metadata = evidence.get("metadata") or {}

        raw = (
            evidence.get("source_reliability")
            or metadata.get("source_reliability")
            or metadata.get("reliability_score")
            or 70
        )

        try:
            value = float(raw)
        except Exception:
            value = 70.0

        return self._bounded(value / 100.0)

    def _corroboration_score(
        self,
        evidence: dict[str, Any],
    ) -> float:
        metadata = evidence.get("metadata") or {}

        raw = (
            evidence.get("source_diversity_count")
            or metadata.get("source_diversity_count")
            or 1
        )

        try:
            count = max(1, int(raw))
        except Exception:
            count = 1

        # Only distinct sources increase corroboration confidence.
        # Repeated reporting from the same source does not.
        return self._bounded((count - 1) / 3.0)

    def _lexical_scores(
        self,
        *,
        evidence: dict[str, Any],
        indicator: dict[str, Any],
        mapping: dict[str, Any],
    ) -> tuple[float, float, list[str]]:
        evidence_terms = self._terms(
            evidence.get("title"),
            evidence.get("raw_text"),
            evidence.get("metadata"),
        )

        specific_terms = self._terms(
            indicator.get("indicator_key"),
            indicator.get("name"),
            indicator.get("tags"),
            indicator.get("sector_scope"),
        )

        context_terms = self._terms(
            indicator.get("description"),
            mapping.get("rationale"),
        )

        specific_overlap = evidence_terms & specific_terms
        context_overlap = evidence_terms & context_terms
        combined = sorted(specific_overlap | context_overlap)

        specific_score = self._bounded(
            len(specific_overlap)
            / max(1, min(5, len(specific_terms)))
        )

        union = evidence_terms | specific_terms | context_terms
        semantic_proxy = (
            len(evidence_terms & (specific_terms | context_terms))
            / max(1, len(union))
        )

        return (
            specific_score,
            self._bounded(semantic_proxy * 4.0),
            combined,
        )

    @staticmethod
    def _concept_key(indicator_key: str) -> str:
        for suffix in (
            "_PRECURSOR",
            "_ACCELERANT",
            "_TRIGGER",
            "_CONTRA",
        ):
            if indicator_key.endswith(suffix):
                return indicator_key[:-len(suffix)]

        return indicator_key

    def _preferred_class(
        self,
        evidence: dict[str, Any],
    ) -> str:
        text = " ".join(
            str(value or "")
            for value in (
                evidence.get("title"),
                evidence.get("raw_text"),
            )
        ).lower()

        contra_terms = {
            "reopened", "reopening", "de-escalation",
            "deescalation", "ceasefire", "restrictions lifted",
            "traffic restored", "transit restored",
        }

        trigger_terms = {
            "closure", "closed", "blockade", "blocked",
            "attack", "strike", "disruption", "disrupted",
            "interdiction", "mining",
        }

        accelerant_terms = {
            "intensify", "intensifies", "intensified",
            "expands", "expanded", "surge", "rising",
            "increase", "increased", "escalation",
        }

        if any(term in text for term in contra_terms):
            return "CONTRA"

        if any(term in text for term in trigger_terms):
            return "TRIGGER"

        if any(term in text for term in accelerant_terms):
            return "ACCELERANT"

        return "PRECURSOR"

    def score(
        self,
        *,
        evidence: dict[str, Any],
        indicator: dict[str, Any],
        mapping: dict[str, Any],
    ) -> IndicatorMatch | None:
        lexical, semantic, matched_terms = self._lexical_scores(
            evidence=evidence,
            indicator=indicator,
            mapping=mapping,
        )

        if not matched_terms:
            return None

        reliability = self._source_reliability(evidence)
        freshness = self._freshness_score(evidence)
        corroboration = self._corroboration_score(evidence)

        indicator_class = str(
            mapping.get("indicator_class")
            or indicator.get("default_class")
            or "PRECURSOR"
        ).upper()

        preferred_class = self._preferred_class(evidence)

        class_alignment = (
            1.0
            if indicator_class == preferred_class
            else 0.35
        )

        contradiction_penalty = (
            0.15
            if (
                indicator_class == "CONTRA"
                and preferred_class != "CONTRA"
            )
            else 0.0
        )

        final_score = (
            lexical * 0.35
            + semantic * 0.25
            + reliability * 0.15
            + freshness * 0.10
            + corroboration * 0.05
            + class_alignment * 0.10
            - contradiction_penalty
        )

        if final_score < 0.32:
            return None

        return IndicatorMatch(
            indicator_key=indicator["indicator_key"],
            score=round(self._bounded(final_score), 6),
            matched_terms=matched_terms[:12],
            polarity=self.CLASS_POLARITY.get(
                indicator_class,
                "NEUTRAL",
            ),
            score_breakdown={
                "lexical_relevance": round(lexical, 4),
                "semantic_similarity": round(semantic, 4),
                "source_reliability": round(reliability, 4),
                "freshness": round(freshness, 4),
                "corroboration": round(corroboration, 4),
                "class_alignment": round(class_alignment, 4),
                "contradiction_penalty": round(
                    contradiction_penalty,
                    4,
                ),
                "final_score": round(
                    self._bounded(final_score),
                    4,
                ),
            },
        )

    def rank_for_evidence(
        self,
        *,
        evidence: dict[str, Any],
        mappings: list[dict[str, Any]],
        limit: int = 4,
    ) -> list[tuple[dict[str, Any], IndicatorMatch]]:
        best_by_concept: dict[
            str,
            tuple[dict[str, Any], IndicatorMatch],
        ] = {}

        for mapping in mappings:
            indicator = (
                mapping.get("sews_indicator_definitions")
                or {}
            )

            match = self.score(
                evidence=evidence,
                indicator=indicator,
                mapping=mapping,
            )

            if match is None:
                continue

            concept_key = self._concept_key(
                mapping["indicator_key"]
            )

            current = best_by_concept.get(concept_key)

            if (
                current is None
                or match.score > current[1].score
            ):
                best_by_concept[concept_key] = (
                    mapping,
                    match,
                )

        ranked = sorted(
            best_by_concept.values(),
            key=lambda item: (
                item[1].score,
                float(item[0].get("weight") or 1.0),
            ),
            reverse=True,
        )

        return ranked[:limit]

    def match(
        self,
        *,
        evidence: dict[str, Any],
        indicator: dict[str, Any],
        mapping: dict[str, Any],
    ) -> IndicatorMatch | None:
        return self.score(
            evidence=evidence,
            indicator=indicator,
            mapping=mapping,
        )
