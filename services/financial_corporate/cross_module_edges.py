from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional


@dataclass(frozen=True)
class ExposureEdge:
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    weight: float
    source_module: str
    confidence: float
    evidence: Dict[str, Any]
    observed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CrossModuleExposureBridge:
    """Normalize cross-module evidence into directed corporate exposure edges.

    Weight is a bounded 0-1 economic dependency/exposure coefficient. Confidence is
    0-100 and kept separate from the weight. Source modules provide evidence; this
    bridge converts that evidence into one graph contract for Financial/Corporate
    contagion analysis.
    """

    MODULES = {
        "supply_chain": "Supply Chain Intelligence",
        "country": "Country Intelligence",
        "conflict": "Conflict Forecasting",
        "sanctions": "Sanctions / Trade Intelligence",
        "cyber": "Cyber & Information Operations",
    }

    @staticmethod
    def _clamp01(value: Any) -> float:
        try:
            return round(max(0.0, min(1.0, float(value))), 4)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _clamp100(value: Any, default: float = 60.0) -> float:
        try:
            return round(max(0.0, min(100.0, float(value))), 2)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _edge(
        self,
        source: str,
        target: str,
        relationship_type: str,
        weight: float,
        source_module: str,
        confidence: float,
        evidence: Mapping[str, Any],
    ) -> Optional[ExposureEdge]:
        if not source or not target or source == target:
            return None
        weight = self._clamp01(weight)
        if weight <= 0:
            return None
        return ExposureEdge(
            source_entity_id=str(source),
            target_entity_id=str(target),
            relationship_type=relationship_type,
            weight=weight,
            source_module=source_module,
            confidence=self._clamp100(confidence),
            evidence=dict(evidence),
            observed_at=str(evidence.get("observed_at") or self._now()),
        )

    def from_supply_chain(self, records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        edges: List[ExposureEdge] = []
        for row in records:
            company = str(row.get("company_entity_id") or row.get("target_entity_id") or "")
            dependency = str(
                row.get("dependency_entity_id")
                or row.get("source_entity_id")
                or row.get("supplier_entity_id")
                or row.get("facility_id")
                or row.get("port_id")
                or row.get("chokepoint_id")
                or row.get("commodity_id")
                or ""
            )
            relationship = str(row.get("relationship_type") or "supply_chain_dependency")
            share = row.get("dependency_share")
            if share is None:
                share = row.get("weight")
            if share is None:
                share = row.get("exposure_share")
            try:
                share_f = float(share or 0.0)
            except (TypeError, ValueError):
                share_f = 0.0
            if share_f > 1.0:
                share_f /= 100.0
            edge = self._edge(
                dependency,
                company,
                relationship,
                share_f,
                self.MODULES["supply_chain"],
                row.get("confidence", 75),
                row,
            )
            if edge:
                edges.append(edge)
        return [edge.to_dict() for edge in edges]

    def from_country(self, records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        edges: List[ExposureEdge] = []
        for row in records:
            company = str(row.get("company_entity_id") or row.get("target_entity_id") or "")
            iso3 = str(row.get("country_iso3") or row.get("iso3") or "").upper()
            if not iso3:
                continue
            exposure = row.get("revenue_share")
            if exposure is None:
                exposure = row.get("asset_share")
            if exposure is None:
                exposure = row.get("exposure_share")
            if exposure is None:
                exposure = row.get("weight")
            try:
                exposure_f = float(exposure or 0.0)
            except (TypeError, ValueError):
                exposure_f = 0.0
            if exposure_f > 1.0:
                exposure_f /= 100.0
            edge = self._edge(
                f"country:{iso3}",
                company,
                str(row.get("relationship_type") or "country_exposure"),
                exposure_f,
                self.MODULES["country"],
                row.get("confidence", 70),
                row,
            )
            if edge:
                edges.append(edge)
        return [edge.to_dict() for edge in edges]

    def from_conflict(self, records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        edges: List[ExposureEdge] = []
        for row in records:
            company = str(row.get("company_entity_id") or row.get("target_entity_id") or "")
            conflict_id = str(row.get("conflict_id") or row.get("scenario_id") or row.get("source_entity_id") or "")
            if not conflict_id:
                continue
            exposure = row.get("exposure_weight")
            if exposure is None:
                exposure = row.get("weight")
            if exposure is None:
                severity = self._clamp100(row.get("severity_score", row.get("risk_score", 0))) / 100.0
                geographic = self._clamp100(row.get("geographic_relevance", 100)) / 100.0
                exposure = severity * geographic
            edge = self._edge(
                f"conflict:{conflict_id}" if not conflict_id.startswith("conflict:") else conflict_id,
                company,
                str(row.get("relationship_type") or "conflict_exposure"),
                float(exposure or 0.0),
                self.MODULES["conflict"],
                row.get("confidence", 65),
                row,
            )
            if edge:
                edges.append(edge)
        return [edge.to_dict() for edge in edges]

    def from_sanctions(self, records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        edges: List[ExposureEdge] = []
        for row in records:
            company = str(row.get("company_entity_id") or row.get("target_entity_id") or "")
            counterparty = str(row.get("counterparty_entity_id") or row.get("source_entity_id") or row.get("sanctioned_entity_id") or "")
            exposure = row.get("transaction_share")
            if exposure is None:
                exposure = row.get("exposure_weight")
            if exposure is None:
                exposure = row.get("weight", 1.0 if row.get("direct_match") else 0.5)
            try:
                exposure_f = float(exposure or 0.0)
            except (TypeError, ValueError):
                exposure_f = 0.0
            if exposure_f > 1.0:
                exposure_f /= 100.0
            edge = self._edge(
                counterparty,
                company,
                str(row.get("relationship_type") or "sanctions_counterparty_exposure"),
                exposure_f,
                self.MODULES["sanctions"],
                row.get("confidence", 85),
                row,
            )
            if edge:
                edges.append(edge)
        return [edge.to_dict() for edge in edges]

    def from_cyber(self, records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        edges: List[ExposureEdge] = []
        for row in records:
            company = str(row.get("company_entity_id") or row.get("target_entity_id") or "")
            source = str(row.get("incident_id") or row.get("campaign_id") or row.get("actor_id") or row.get("source_entity_id") or "")
            severity = self._clamp100(row.get("severity_score", row.get("risk_score", 0))) / 100.0
            exposure = row.get("exposure_weight")
            if exposure is None:
                exposure = severity * (self._clamp100(row.get("business_impact", 70)) / 100.0)
            edge = self._edge(
                f"cyber:{source}" if source and not source.startswith("cyber:") else source,
                company,
                str(row.get("relationship_type") or "cyber_operational_exposure"),
                float(exposure or 0.0),
                self.MODULES["cyber"],
                row.get("confidence", 60),
                row,
            )
            if edge:
                edges.append(edge)
        return [edge.to_dict() for edge in edges]

    def build(self, module_payloads: Mapping[str, Iterable[Mapping[str, Any]]]) -> Dict[str, Any]:
        all_edges: List[Dict[str, Any]] = []
        by_module: Dict[str, int] = {}
        adapters = {
            "supply_chain": self.from_supply_chain,
            "country": self.from_country,
            "conflict": self.from_conflict,
            "sanctions": self.from_sanctions,
            "cyber": self.from_cyber,
        }
        for key, adapter in adapters.items():
            rows = list(module_payloads.get(key) or [])
            normalized = adapter(rows)
            all_edges.extend(normalized)
            by_module[key] = len(normalized)

        dedup: Dict[tuple[str, str, str], Dict[str, Any]] = {}
        for edge in all_edges:
            key = (edge["source_entity_id"], edge["target_entity_id"], edge["relationship_type"])
            current = dedup.get(key)
            if current is None or edge["confidence"] > current["confidence"]:
                dedup[key] = edge

        target_counts = defaultdict(int)
        for edge in dedup.values():
            target_counts[edge["target_entity_id"]] += 1

        return {
            "edges": list(dedup.values()),
            "edge_count": len(dedup),
            "by_module": by_module,
            "targets": dict(sorted(target_counts.items(), key=lambda item: item[1], reverse=True)),
            "schema": "cross_module_exposure_edge_v1",
            "ai_generated": False,
        }
