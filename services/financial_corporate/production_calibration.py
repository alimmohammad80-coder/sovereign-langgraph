from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .calibrated_hazards import CalibratedCorporateHazardService
from .sec_edgar import SECConfigurationError, SEC_DATA_BASE, SECEdgarCollector


class ProductionCalibratedCorporateHazardService(CalibratedCorporateHazardService):
    """Final semantic calibration for Governance / Operational Risk.

    The preceding calibrated layer improves freshness and source quality. This
    layer fixes a different problem: product vulnerabilities, enterprise cyber
    incidents, active exploitation, and corporate operational risk are not the
    same thing and must not be combined with a noisy-OR aggregator.

    The operational composite therefore keeps separate subcomponents:
    - authoritative SEC Item 1.05 material-cyber disclosures;
    - direct company cyber incidents from current reporting;
    - CISA KEV / active exploitation pressure;
    - NVD product-security pressure, explicitly capped;
    - broader cyber-media context, explicitly capped.

    Missing evidence remains missing. Scores are deterministic operational risk
    indices and are not probabilities of compromise.
    """

    SEC_CYBER_LOOKBACK_DAYS = 365

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sec = SECEdgarCollector()

    @staticmethod
    def _days_old(value: Any) -> Optional[float]:
        dt = ProductionCalibratedCorporateHazardService._parse_datetime(value)
        if dt is None:
            return None
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)

    def sec_material_cyber_disclosure(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        identifiers = entity.get("identifiers") or {}
        cik = identifiers.get("cik") if isinstance(identifiers, Mapping) else None
        if not cik:
            return {
                "status": "missing",
                "score": None,
                "source": "SEC EDGAR",
                "reason": "missing_cik",
            }
        if not self.sec.configured:
            return {
                "status": "unavailable",
                "score": None,
                "source": "SEC EDGAR",
                "reason": "SEC_USER_AGENT_not_configured",
            }

        try:
            cik10 = self.sec.normalize_cik(cik)
            raw = self.sec._get_json(f"{SEC_DATA_BASE}/submissions/CIK{cik10}.json")
            recent = ((raw.get("filings") or {}).get("recent") or {})
            forms = recent.get("form") or []
            filed = recent.get("filingDate") or []
            items = recent.get("items") or []
            accessions = recent.get("accessionNumber") or []
            docs = recent.get("primaryDocument") or []
            matches: List[Dict[str, Any]] = []

            for index, form in enumerate(forms):
                if str(form or "").upper() not in {"8-K", "8-K/A"}:
                    continue
                filing_items = str(items[index] if index < len(items) else "")
                if "1.05" not in filing_items:
                    continue
                filing_date = filed[index] if index < len(filed) else None
                age_days = self._days_old(filing_date)
                if age_days is None or age_days > self.SEC_CYBER_LOOKBACK_DAYS:
                    continue
                matches.append({
                    "form": form,
                    "filing_date": filing_date,
                    "items": filing_items,
                    "accession_number": accessions[index] if index < len(accessions) else None,
                    "primary_document": docs[index] if index < len(docs) else None,
                    "age_days": round(age_days, 2),
                })

            if not matches:
                return {
                    "status": "screened_no_recent_item_1_05",
                    "score": None,
                    "source": "SEC EDGAR submissions",
                    "source_url": f"{SEC_DATA_BASE}/submissions/CIK{cik10}.json",
                    "lookback_days": self.SEC_CYBER_LOOKBACK_DAYS,
                    "caveat": "No recent Item 1.05 filing does not establish that no cyber incident occurred.",
                }

            latest_age = min(float(item["age_days"]) for item in matches)
            if latest_age <= 30:
                score = 90.0
            elif latest_age <= 90:
                score = 82.0
            elif latest_age <= 180:
                score = 72.0
            else:
                score = 62.0
            return {
                "status": "observed",
                "score": score,
                "confidence": 98.0,
                "source": "SEC EDGAR submissions",
                "source_url": f"{SEC_DATA_BASE}/submissions/CIK{cik10}.json",
                "lookback_days": self.SEC_CYBER_LOOKBACK_DAYS,
                "matched_count": len(matches),
                "matched_filings": matches[:5],
                "methodology": "sec_8k_item_1_05_material_cyber_disclosure_v1",
                "caveat": "Item 1.05 is treated as authoritative disclosure evidence, not a probability of compromise.",
            }
        except SECConfigurationError as exc:
            return {"status": "unavailable", "score": None, "source": "SEC EDGAR", "error": str(exc)}
        except Exception as exc:
            return {"status": "error", "score": None, "source": "SEC EDGAR", "error": str(exc)[:240]}

    @classmethod
    def direct_enterprise_incident_pressure(
        cls,
        entity: Mapping[str, Any],
        cyber_media: Mapping[str, Any],
    ) -> Dict[str, Any]:
        names = cls._company_tokens(entity)
        incident_terms = ["data breach", "breached", "cyberattack", "ransomware", "security incident"]
        matched: List[Dict[str, Any]] = []
        points = 0.0

        for item in cyber_media.get("matched_items") or []:
            title = str(item.get("title") or "")
            lower = title.lower()
            if not any(name in lower for name in names):
                continue

            proximity = False
            for name in names:
                name_pos = lower.find(name)
                if name_pos < 0:
                    continue
                for term in incident_terms:
                    term_pos = lower.find(term)
                    if term_pos >= 0 and abs(term_pos - name_pos) <= 55:
                        proximity = True
                        break
                if proximity:
                    break
            if not proximity:
                continue

            # Supplier/customer incidents that only mention the company as a
            # downstream party remain ecosystem context, not enterprise incidents.
            if str(item.get("relevance") or "") == "ecosystem":
                continue

            source_weight = float(item.get("source_quality_weight") or 0.6)
            freshness_weight = float(item.get("freshness_weight") or 0.5)
            severity_multiplier = 1.0 if item.get("signal_severity") == "high" else 0.55
            contribution = 22.0 * source_weight * freshness_weight * severity_multiplier
            points += contribution
            matched.append({**dict(item), "enterprise_incident_points": round(contribution, 2)})

        if not matched:
            return {
                "status": "screened_no_direct_enterprise_incident",
                "score": None,
                "confidence": None,
                "source": "quality-weighted cyber reporting",
                "caveat": "No direct media incident signal does not establish zero enterprise cyber risk.",
            }

        score = min(82.0, 48.0 + points)
        avg_quality = sum(float(item.get("source_quality_weight") or 0.6) for item in matched) / len(matched)
        confidence = min(92.0, 68.0 + min(len(matched), 4) * 4.0 + avg_quality * 8.0)
        return {
            "status": "observed",
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "source": "quality-weighted cyber reporting",
            "matched_count": len(matched),
            "matched_items": matched[:5],
            "methodology": "direct_enterprise_cyber_incident_pressure_v1",
        }

    @staticmethod
    def _component(signal: Mapping[str, Any], *, cap: Optional[float], weight: float, label: str) -> Optional[Dict[str, Any]]:
        if signal.get("score") is None:
            return None
        try:
            raw_score = max(0.0, min(100.0, float(signal.get("score"))))
            confidence = max(0.0, min(100.0, float(signal.get("confidence") or 60.0)))
        except (TypeError, ValueError):
            return None
        score = min(raw_score, cap) if cap is not None else raw_score
        return {
            "component": label,
            "raw_score": round(raw_score, 2),
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "base_weight": weight,
        }

    @classmethod
    def governance_operational_composite(
        cls,
        *,
        sec_disclosure: Mapping[str, Any],
        enterprise_incident: Mapping[str, Any],
        cisa_kev: Mapping[str, Any],
        nvd: Mapping[str, Any],
        cyber_media: Mapping[str, Any],
    ) -> Dict[str, Any]:
        candidates = [
            cls._component(sec_disclosure, cap=None, weight=0.40, label="sec_material_cyber_disclosure"),
            cls._component(enterprise_incident, cap=82.0, weight=0.35, label="direct_enterprise_cyber_incident"),
            cls._component(cisa_kev, cap=85.0, weight=0.15, label="active_exploitation_cisa_kev"),
            cls._component(nvd, cap=55.0, weight=0.07, label="product_security_nvd"),
            cls._component(cyber_media, cap=35.0, weight=0.03, label="cyber_media_context"),
        ]
        components = [item for item in candidates if item is not None]
        if not components:
            return {
                "status": "missing",
                "score": None,
                "confidence": None,
                "components": [],
                "methodology": "governance_operational_semantic_composite_v1",
            }

        denominator = sum(float(item["base_weight"]) for item in components)
        score = sum(float(item["score"]) * float(item["base_weight"]) for item in components) / denominator
        confidence = sum(float(item["confidence"]) * float(item["base_weight"]) for item in components) / denominator
        return {
            "status": "observed",
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "components": components,
            "effective_weight_sum": round(denominator, 4),
            "methodology": "governance_operational_semantic_composite_v1",
            "interpretation": "Corporate operational pressure composite; product vulnerability evidence is capped and cannot dominate the dimension.",
        }

    def enrich(self, *, company_entity_id: str, entity: Mapping[str, Any], edges: List[Mapping[str, Any]]) -> Dict[str, Any]:
        result = super().enrich(company_entity_id=company_entity_id, entity=entity, edges=edges)

        cisa = dict(result.get("cyber_screening") or {})
        nvd = dict(result.get("cyber_nvd_pressure") or {})
        cyber_media = dict(result.get("cyber_media_pressure") or {})
        sec_disclosure = self.sec_material_cyber_disclosure(entity)
        enterprise_incident = self.direct_enterprise_incident_pressure(entity, cyber_media)
        composite = self.governance_operational_composite(
            sec_disclosure=sec_disclosure,
            enterprise_incident=enterprise_incident,
            cisa_kev=cisa,
            nvd=nvd,
            cyber_media=cyber_media,
        )

        scoped_edges = [
            dict(edge) for edge in (result.get("edges") or [])
            if str(edge.get("source_entity_id") or "") != "cyber:company-operational-pressure"
        ]
        if composite.get("score") is not None:
            scoped_edges.append({
                "source_entity_id": "operational:company-semantic-composite",
                "target_entity_id": company_entity_id,
                "relationship_type": "company_governance_operational_pressure",
                "weight": 1.0,
                "source_module": "Cyber & Information Operations",
                "confidence": composite.get("confidence"),
                "evidence": {
                    "structural_exposure": 1.0,
                    "hazard_score": composite.get("score"),
                    "hazard_source": "governance_operational_semantic_composite_v1",
                    "sec_material_cyber_disclosure": sec_disclosure,
                    "direct_enterprise_incident": enterprise_incident,
                    "cisa_kev": cisa,
                    "product_security_nvd": nvd,
                    "cyber_media_context": cyber_media,
                    "composite": composite,
                },
                "observed_at": datetime.now(timezone.utc).isoformat(),
            })

        result["edges"] = scoped_edges
        result["sec_material_cyber_disclosure"] = sec_disclosure
        result["direct_enterprise_cyber_incident"] = enterprise_incident
        result["governance_operational_composite"] = composite
        result["methodology"] = "cross_module_dynamic_hazard_enrichment_v4_semantic_operational_calibration"
        result["operational_calibration_rules"] = [
            "SEC Form 8-K Item 1.05 is the highest-confidence material cyber-incident signal when present.",
            "Direct enterprise incidents are separated from supplier/customer ecosystem incidents.",
            "NVD product-security pressure is capped at 55 inside Governance / Operational Risk.",
            "General cyber-media context is capped at 35 and receives only a small composite weight.",
            "Product vulnerabilities cannot by themselves create a critical corporate operational score.",
        ]
        return result
