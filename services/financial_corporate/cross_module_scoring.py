from __future__ import annotations

from collections import defaultdict
from math import prod
from typing import Any, Dict, Iterable, List, Mapping, Optional


class CrossModuleRiskScorer:
    """Convert evidence-bearing exposure edges into corporate risk dimensions.

    Exposure weight and evidence confidence are not themselves risk. A numeric
    dimension is produced only when the source record contains an explicit risk,
    severity, disruption, or impact score. This prevents the bridge from
    fabricating risk where only a relationship is known.
    """

    MODULE_MAP = {
        "Supply Chain Intelligence": "supply_chain",
        "Country Intelligence": "geopolitical",
        "Conflict Forecasting": "geopolitical",
        "Sanctions / Trade Intelligence": "sanctions_compliance",
        "Cyber & Information Operations": "governance_operational",
    }

    SCORE_KEYS = (
        "risk_score",
        "severity_score",
        "disruption_probability",
        "impact_score",
        "business_impact",
        "country_risk_score",
        "conflict_risk_score",
        "sanctions_risk_score",
        "cyber_risk_score",
        "post_shock_risk_score",
        "score",
    )

    @staticmethod
    def _score(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            number = float(value)
        except (TypeError, ValueError):
            return None
        if 0.0 <= number <= 1.0:
            number *= 100.0
        return max(0.0, min(100.0, number))

    def _edge_intensity(self, edge: Mapping[str, Any]) -> Optional[float]:
        evidence = edge.get("evidence") or {}
        if not isinstance(evidence, Mapping):
            return None
        for key in self.SCORE_KEYS:
            value = self._score(evidence.get(key))
            if value is not None:
                return value
        return None

    @staticmethod
    def _combined(contributions: Iterable[float]) -> Optional[float]:
        values = [max(0.0, min(100.0, float(v))) for v in contributions]
        if not values:
            return None
        # Bounded union of independent stress contributions. This rewards
        # multiple corroborating exposures without allowing scores > 100.
        combined = 100.0 * (1.0 - prod(1.0 - value / 100.0 for value in values))
        return round(combined, 2)

    def score_company(self, company_entity_id: str, edges: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        company_edges = [
            dict(edge)
            for edge in edges
            if str(edge.get("target_entity_id") or "") == company_entity_id
        ]

        by_dimension: Dict[str, List[float]] = defaultdict(list)
        evidence_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for edge in company_edges:
            dimension = self.MODULE_MAP.get(str(edge.get("source_module") or ""))
            if not dimension:
                continue
            intensity = self._edge_intensity(edge)
            if intensity is None:
                continue
            try:
                exposure = max(0.0, min(1.0, float(edge.get("weight") or 0.0)))
                confidence = max(0.0, min(100.0, float(edge.get("confidence") or 0.0))) / 100.0
            except (TypeError, ValueError):
                continue
            contribution = intensity * exposure * confidence
            by_dimension[dimension].append(contribution)
            evidence_rows[dimension].append({
                "source_entity_id": edge.get("source_entity_id"),
                "relationship_type": edge.get("relationship_type"),
                "source_module": edge.get("source_module"),
                "risk_intensity": round(intensity, 2),
                "exposure_weight": round(exposure, 4),
                "confidence": round(confidence * 100.0, 2),
                "risk_contribution": round(contribution, 2),
            })

        scores = {
            dimension: self._combined(by_dimension.get(dimension, []))
            for dimension in (
                "supply_chain",
                "geopolitical",
                "sanctions_compliance",
                "governance_operational",
            )
        }

        return {
            "company_entity_id": company_entity_id,
            "scores": scores,
            "evidence": dict(evidence_rows),
            "matched_edge_count": len(company_edges),
            "scored_edge_count": sum(len(rows) for rows in evidence_rows.values()),
            "methodology": "cross_module_evidence_weighted_risk_v1",
            "ai_generated_score": False,
        }
