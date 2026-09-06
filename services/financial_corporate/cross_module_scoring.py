from __future__ import annotations

from collections import defaultdict
from math import prod
from typing import Any, Dict, Iterable, List, Mapping, Optional


class CrossModuleRiskScorer:
    """Score corporate cross-module risk as exposure x hazard x confidence.

    Structural exposure answers how dependent the company is on an entity or
    pathway. Dynamic hazard answers how stressed that source is now. Evidence
    confidence remains separate. A structural exposure without a current hazard
    is not converted into a numeric risk score.
    """

    MODULE_MAP = {
        "Supply Chain Intelligence": "supply_chain",
        "Country Intelligence": "geopolitical",
        "Conflict Forecasting": "geopolitical",
        "Sanctions / Trade Intelligence": "sanctions_compliance",
        "Cyber & Information Operations": "governance_operational",
    }

    HAZARD_KEYS = (
        "hazard_score",
        "hazard_intensity",
        "country_risk_score",
        "conflict_risk_score",
        "sanctions_risk_score",
        "cyber_risk_score",
        "disruption_probability",
        "impact_score",
        "business_impact",
        "post_shock_risk_score",
        "risk_score",
        "score",
    )

    LEGACY_SEVERITY_KEYS = ("severity_score",)

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

    @staticmethod
    def _exposure(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number > 1.0:
            number /= 100.0
        return max(0.0, min(1.0, number))

    def _edge_hazard(self, edge: Mapping[str, Any]) -> tuple[Optional[float], Optional[str]]:
        evidence = edge.get("evidence") or {}
        if not isinstance(evidence, Mapping):
            return None, None
        for key in self.HAZARD_KEYS:
            value = self._score(evidence.get(key))
            if value is not None:
                return value, str(evidence.get("hazard_source") or key)

        # Backward compatibility for genuine severity-bearing legacy edges.
        # A stored corporate exposure level is structural exposure, not hazard.
        if str(evidence.get("severity_source") or "") != "stored_exposure_level":
            for key in self.LEGACY_SEVERITY_KEYS:
                value = self._score(evidence.get(key))
                if value is not None:
                    return value, str(evidence.get("severity_source") or key)
        return None, None

    def _edge_exposure(self, edge: Mapping[str, Any]) -> Optional[float]:
        evidence = edge.get("evidence") or {}
        if isinstance(evidence, Mapping):
            value = self._exposure(evidence.get("structural_exposure"))
            if value is not None:
                return value
            value = self._exposure(evidence.get("exposure_level"))
            if value is not None:
                return value
        return self._exposure(edge.get("weight"))

    @staticmethod
    def _combined(contributions: Iterable[float]) -> Optional[float]:
        values = [max(0.0, min(100.0, float(v))) for v in contributions]
        if not values:
            return None
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
        unscored_rows: List[Dict[str, Any]] = []

        for edge in company_edges:
            dimension = self.MODULE_MAP.get(str(edge.get("source_module") or ""))
            if not dimension:
                continue
            hazard, hazard_source = self._edge_hazard(edge)
            exposure = self._edge_exposure(edge)
            try:
                confidence = max(0.0, min(100.0, float(edge.get("confidence") or 0.0))) / 100.0
            except (TypeError, ValueError):
                confidence = 0.0

            if hazard is None or exposure is None or exposure <= 0.0 or confidence <= 0.0:
                unscored_rows.append({
                    "source_entity_id": edge.get("source_entity_id"),
                    "relationship_type": edge.get("relationship_type"),
                    "source_module": edge.get("source_module"),
                    "dimension": dimension,
                    "structural_exposure": round(exposure, 4) if exposure is not None else None,
                    "hazard_intensity": round(hazard, 2) if hazard is not None else None,
                    "reason": "missing_dynamic_hazard" if hazard is None else "insufficient_exposure_or_confidence",
                })
                continue

            contribution = hazard * exposure * confidence
            by_dimension[dimension].append(contribution)
            evidence_rows[dimension].append({
                "source_entity_id": edge.get("source_entity_id"),
                "relationship_type": edge.get("relationship_type"),
                "source_module": edge.get("source_module"),
                "structural_exposure": round(exposure, 4),
                "hazard_intensity": round(hazard, 2),
                "hazard_source": hazard_source,
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
            "unscored_exposures": unscored_rows,
            "matched_edge_count": len(company_edges),
            "scored_edge_count": sum(len(rows) for rows in evidence_rows.values()),
            "methodology": "cross_module_exposure_hazard_confidence_v2",
            "formula": "risk_contribution = hazard_intensity * structural_exposure * evidence_confidence",
            "ai_generated_score": False,
        }
