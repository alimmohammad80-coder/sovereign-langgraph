from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z0-9]{3,}")

@dataclass(slots=True)
class IndicatorMatch:
    indicator_key: str
    score: float
    matched_terms: list[str]
    polarity: str

class SEWSDeterministicIndicatorMatcher:
    STOPWORDS = {
        "the","and","for","with","from","that","this","warning","indicator",
        "strategic","risk","activity","event","events","evidence","current",
        "change","changes","system","monitoring","assess","assessment",
        "relevant","related","source","sources","energy","security","supply",
        "chain","conflict","military","economic","financial","political",
        "humanitarian","public","health","operations","domain","regional",
        "global","report","reports","news",
    }
    CLASS_POLARITY = {
        "PRECURSOR":"SUPPORTING","ACCELERANT":"SUPPORTING",
        "TRIGGER":"SUPPORTING","CONTRA":"CONTRADICTING",
    }

    @classmethod
    def _terms(cls, *values: Any) -> set[str]:
        out = set()
        for value in values:
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                out |= cls._terms(*value)
                continue
            if isinstance(value, dict):
                out |= cls._terms(*value.keys(), *value.values())
                continue
            normalized = str(value).lower().replace("_", " ")
            out |= {
                t for t in TOKEN_RE.findall(normalized)
                if t not in cls.STOPWORDS
            }
        return out

    def score(self, *, evidence, indicator, mapping):
        evidence_terms = self._terms(
            evidence.get("title"), evidence.get("raw_text"),
            evidence.get("metadata"),
        )
        specific_terms = self._terms(
            indicator.get("indicator_key"), indicator.get("name"),
            indicator.get("tags"), indicator.get("sector_scope"),
        )
        context_terms = self._terms(
            indicator.get("description"), mapping.get("rationale"),
        )
        specific_overlap = sorted(evidence_terms & specific_terms)
        context_overlap = sorted(evidence_terms & context_terms)
        combined = sorted(set(specific_overlap) | set(context_overlap))

        if len(specific_overlap) < 1 or len(combined) < 2:
            return None

        score = (
            min(1.0, len(specific_overlap) / 5.0) * 0.85
            + min(1.0, len(context_overlap) / 6.0) * 0.15
        )
        if score < 0.28:
            return None

        indicator_class = str(
            mapping.get("indicator_class")
            or indicator.get("default_class")
            or "PRECURSOR"
        ).upper()

        return IndicatorMatch(
            indicator_key=indicator["indicator_key"],
            score=round(score, 6),
            matched_terms=combined[:12],
            polarity=self.CLASS_POLARITY.get(indicator_class, "NEUTRAL"),
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
            "reopened",
            "reopening",
            "de-escalation",
            "deescalation",
            "ceasefire",
            "restrictions lifted",
            "traffic restored",
            "transit restored",
        }

        trigger_terms = {
            "closure",
            "closed",
            "blockade",
            "blocked",
            "attack",
            "strike",
            "disruption",
            "disrupted",
            "interdiction",
            "mining",
        }

        accelerant_terms = {
            "intensify",
            "intensifies",
            "intensified",
            "expands",
            "expanded",
            "surge",
            "rising",
            "increase",
            "increased",
            "escalation",
        }

        if any(term in text for term in contra_terms):
            return "CONTRA"

        if any(term in text for term in trigger_terms):
            return "TRIGGER"

        if any(term in text for term in accelerant_terms):
            return "ACCELERANT"

        return "PRECURSOR"

    def rank_for_evidence(
        self,
        *,
        evidence,
        mappings,
        limit=4,
    ):
        preferred_class = self._preferred_class(evidence)

        best_by_concept = {}

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

            indicator_class = str(
                mapping.get("indicator_class")
                or ""
            ).upper()

            concept_key = self._concept_key(
                mapping["indicator_key"]
            )

            class_bonus = (
                0.20
                if indicator_class == preferred_class
                else 0.0
            )

            ranking_score = match.score + class_bonus

            current = best_by_concept.get(concept_key)

            if (
                current is None
                or ranking_score > current[2]
            ):
                best_by_concept[concept_key] = (
                    mapping,
                    match,
                    ranking_score,
                )

        ranked = sorted(
            best_by_concept.values(),
            key=lambda item: (
                item[2],
                float(item[0].get("weight") or 1.0),
            ),
            reverse=True,
        )

        return [
            (mapping, match)
            for mapping, match, _ in ranked[:limit]
        ]

    def match(self, *, evidence, indicator, mapping):
        return self.score(
            evidence=evidence,
            indicator=indicator,
            mapping=mapping,
        )
