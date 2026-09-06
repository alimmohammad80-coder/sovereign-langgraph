from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping

from .production_calibration import ProductionCalibratedCorporateHazardService


class EvidenceCalibratedCorporateHazardService(ProductionCalibratedCorporateHazardService):
    """Evidence-attribution hardening for production corporate hazards.

    A company mention near words such as ``cyberattack`` or ``breach`` is not
    sufficient to establish that the company was the affected enterprise.
    Direct-enterprise incident evidence must contain an attribution pattern that
    identifies the requested company as the victim, affected entity, or entity
    confirming/disclosing its own incident.
    """

    DIRECT_INCIDENT_METHODOLOGY = "direct_enterprise_cyber_incident_attribution_v2"

    @classmethod
    def _company_name_pattern(cls, entity: Mapping[str, Any]) -> str:
        names = cls._company_tokens(entity)
        if not names:
            return ""
        # Longest aliases first prevents a short alias from consuming a longer
        # legal name in regex alternation.
        return "(?:" + "|".join(re.escape(name) for name in names) + ")"

    @classmethod
    def _is_direct_enterprise_incident_title(cls, entity: Mapping[str, Any], title: Any) -> bool:
        text = " ".join(str(title or "").lower().split())
        company = cls._company_name_pattern(entity)
        if not text or not company:
            return False

        # Company-led attribution: the company confirms/discloses/reports its own
        # breach or is explicitly described as attacked, breached, targeted, etc.
        company_led = [
            rf"\b{company}\b.{{0,45}}\b(?:confirms?|confirmed|discloses?|disclosed|reports?|reported|acknowledges?|acknowledged)\b.{{0,55}}\b(?:data breach|breach|cyberattack|ransomware|security incident)\b",
            rf"\b{company}\b.{{0,25}}\b(?:was |is |has been )?(?:breached|attacked|targeted|compromised|hit)\b(?:.{{0,20}}\bby\b)?",
            rf"\b{company}\b.{{0,30}}\b(?:suffers?|suffered|experiences?|experienced)\b.{{0,35}}\b(?:data breach|breach|cyberattack|ransomware|security incident)\b",
            rf"\b{company}\b.{{0,20}}\b(?:data breach|breach|cyberattack|ransomware|security incident)\b",
        ]

        # Incident-led attribution: "breach at NVIDIA", "ransomware hits NVIDIA",
        # etc. These patterns require the incident predicate to point at the company.
        incident_led = [
            rf"\b(?:data breach|breach|cyberattack|ransomware|security incident)\b.{{0,25}}\b(?:at|against|targeting|affecting)\b.{{0,20}}\b{company}\b",
            rf"\b(?:ransomware|cyberattack|hackers?|attackers?)\b.{{0,25}}\b(?:hits?|hit|targets?|targeted|attacks?|attacked|breaches?|breached|compromises?|compromised)\b.{{0,25}}\b{company}\b",
        ]

        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in company_led + incident_led)

    @classmethod
    def direct_enterprise_incident_pressure(
        cls,
        entity: Mapping[str, Any],
        cyber_media: Mapping[str, Any],
    ) -> Dict[str, Any]:
        matched: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        points = 0.0

        for item in cyber_media.get("matched_items") or []:
            title = str(item.get("title") or "")
            if str(item.get("relevance") or "") == "ecosystem":
                continue
            if not cls._is_direct_enterprise_incident_title(entity, title):
                # Preserve a small diagnostic sample so analysts can see why a
                # co-mention did not become enterprise-incident evidence.
                lower = title.lower()
                if any(name in lower for name in cls._company_tokens(entity)):
                    rejected.append({
                        "title": title,
                        "reason": "company_mentioned_but_not_attributed_as_incident_victim",
                    })
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
                "rejected_co_mentions": rejected[:5],
                "methodology": cls.DIRECT_INCIDENT_METHODOLOGY,
                "caveat": "No directly attributed media incident signal does not establish zero enterprise cyber risk.",
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
            "rejected_co_mentions": rejected[:5],
            "methodology": cls.DIRECT_INCIDENT_METHODOLOGY,
        }

    def enrich(self, *, company_entity_id: str, entity: Mapping[str, Any], edges: List[Mapping[str, Any]]) -> Dict[str, Any]:
        result = super().enrich(company_entity_id=company_entity_id, entity=entity, edges=edges)
        result["methodology"] = "cross_module_dynamic_hazard_enrichment_v5_evidence_attribution"
        result["operational_calibration_rules"] = [
            "SEC Form 8-K Item 1.05 is the highest-confidence material cyber-incident signal when present.",
            "A company co-mention near breach/cyberattack language is not sufficient for direct-enterprise attribution.",
            "Direct enterprise incidents require victim/affected-entity or self-disclosure attribution syntax.",
            "NVD product-security pressure is capped at 55 inside Governance / Operational Risk.",
            "General cyber-media context is capped at 35 and receives only a small composite weight.",
            "Product vulnerabilities cannot by themselves create a critical corporate operational score.",
        ]
        return result
