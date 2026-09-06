from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional

from .production_calibration import ProductionCalibratedCorporateHazardService


class EvidenceCalibratedCorporateHazardService(ProductionCalibratedCorporateHazardService):
    """Evidence-attribution hardening for production corporate hazards.

    This layer enforces two semantic rules that are especially important for the
    Financial & Corporate Risk module:

    1. A company co-mention near cyber language is not enough to establish that
       the company was the affected enterprise.
    2. Export-control pressure is not synonymous with sanctions exposure or a
       compliance violation. Direct restrictions, enforcement, downstream
       diversion, and general policy context are classified separately before a
       company-level regulatory pressure score is produced.
    """

    DIRECT_INCIDENT_METHODOLOGY = "direct_enterprise_cyber_incident_attribution_v2"
    TRADE_CONTROL_METHODOLOGY = "company_trade_control_semantic_attribution_v3"
    CYBER_CONTEXT_METHODOLOGY = "company_cyber_media_semantic_context_v3"

    @classmethod
    def _company_name_pattern(cls, entity: Mapping[str, Any]) -> str:
        names = cls._company_tokens(entity)
        if not names:
            return ""
        return "(?:" + "|".join(re.escape(name) for name in names) + ")"

    @classmethod
    def _is_direct_enterprise_incident_title(cls, entity: Mapping[str, Any], title: Any) -> bool:
        text = " ".join(str(title or "").lower().split())
        company = cls._company_name_pattern(entity)
        if not text or not company:
            return False

        company_led = [
            rf"\b{company}\b.{{0,45}}\b(?:confirms?|confirmed|discloses?|disclosed|reports?|reported|acknowledges?|acknowledged)\b.{{0,55}}\b(?:data breach|breach|cyberattack|ransomware|security incident)\b",
            rf"\b{company}\b.{{0,25}}\b(?:was |is |has been )?(?:breached|attacked|targeted|compromised|hit)\b(?:.{{0,20}}\bby\b)?",
            rf"\b{company}\b.{{0,30}}\b(?:suffers?|suffered|experiences?|experienced)\b.{{0,35}}\b(?:data breach|breach|cyberattack|ransomware|security incident)\b",
            rf"\b{company}\b.{{0,20}}\b(?:data breach|breach|cyberattack|ransomware|security incident)\b",
        ]
        incident_led = [
            rf"\b(?:data breach|breach|cyberattack|ransomware|security incident)\b.{{0,25}}\b(?:at|against|targeting|affecting)\b.{{0,20}}\b{company}\b",
            rf"\b(?:ransomware|cyberattack|hackers?|attackers?)\b.{{0,25}}\b(?:hits?|hit|targets?|targeted|attacks?|attacked|breaches?|breached|compromises?|compromised)\b.{{0,25}}\b{company}\b",
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in company_led + incident_led)

    @classmethod
    def _is_product_security_title(cls, entity: Mapping[str, Any], title: Any) -> bool:
        text = " ".join(str(title or "").lower().split())
        if not text or not any(name in text for name in cls._company_tokens(entity)):
            return False
        security_terms = (
            "vulnerability",
            "vulnerabilities",
            "security flaw",
            "cve-",
            "patch",
            "patches",
            "exploit",
            "zero-day",
            "zero day",
        )
        product_terms = (
            "gpu",
            "driver",
            "geforce",
            "cuda",
            "triton",
            "tensorrt",
            "nemo",
            "nemoclaw",
            "bionemo",
            "firmware",
            "software",
            "server",
        )
        return any(term in text for term in security_terms) and any(term in text for term in product_terms)

    @classmethod
    def _cyber_context_category(cls, entity: Mapping[str, Any], title: Any) -> str:
        text = " ".join(str(title or "").lower().split())
        if cls._is_direct_enterprise_incident_title(entity, title):
            return "direct_enterprise_incident"
        if cls._is_product_security_title(entity, title):
            return "product_security"
        if not any(name in text for name in cls._company_tokens(entity)):
            return "unrelated"

        third_party_incident = re.search(
            r"\b(?:openai|foxconn|supplier|customer|partner|vendor|manufacturer|third[- ]party)\b.{0,80}\b(?:cyberattack|breach|ransomware|hacked|hackers?)\b",
            text,
        )
        if third_party_incident:
            return "ecosystem_incident"
        return "company_context"

    @classmethod
    def _direct_cyber_relevance(cls, entity: Mapping[str, Any], title: Any) -> float:
        category = cls._cyber_context_category(entity, title)
        if category == "direct_enterprise_incident":
            return 1.0
        if category == "product_security":
            return 0.55
        if category == "ecosystem_incident":
            return 0.20
        if category == "company_context":
            return 0.25
        return 0.0

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

    @classmethod
    def _trade_control_category(cls, entity: Mapping[str, Any], title: Any) -> str:
        text = " ".join(str(title or "").lower().split())
        company = cls._company_name_pattern(entity)
        if not text or not company or not re.search(rf"\b{company}\b", text):
            return "unrelated"

        direct_designation_patterns = [
            rf"\b{company}\b.{{0,35}}\b(?:sanctioned|blacklisted|added to (?:the )?entity list|placed on (?:the )?entity list)\b",
            rf"\b(?:sanctions?|blacklist|entity list)\b.{{0,35}}\b(?:against|targets?|targeting|names?)\b.{{0,25}}\b{company}\b",
        ]
        if any(re.search(pattern, text) for pattern in direct_designation_patterns):
            return "direct_sanctions_designation"

        enforcement_patterns = [
            rf"\b(?:bis|commerce department|doj|justice department|regulator|regulators)\b.{{0,45}}\b(?:investigates?|investigating|charges?|charged|fines?|fined|penalizes?|penalized|settles?|settlement|enforcement)\b.{{0,45}}\b{company}\b",
            rf"\b{company}\b.{{0,45}}\b(?:investigation|investigated|charged|fine|fined|penalty|settlement|violation|violated)\b.{{0,40}}\b(?:export|sanctions?|trade|bis|commerce)\b",
        ]
        if any(re.search(pattern, text) for pattern in enforcement_patterns):
            return "compliance_enforcement_exposure"

        downstream_patterns = [
            rf"\b(?:customer|customers|buyer|buyers|military|china|chinese|moonshot|smuggler|reseller|distributor|forwarder)\b.{{0,65}}\b(?:obtains?|obtained|accessed|receives?|received|buys?|bought|reaches?|reached|ships?|shipped)\b.{{0,65}}\b{company}\b",
            rf"\b{company}\b.{{0,55}}\b(?:chips?|servers?|products?)\b.{{0,65}}\b(?:reach|reached|reaching|accessed by|obtained by|smuggled|diverted)\b",
        ]
        if any(re.search(pattern, text) for pattern in downstream_patterns):
            return "downstream_diversion_risk"

        restriction_terms = (
            "export control",
            "export controls",
            "export restriction",
            "export restrictions",
            "license requirement",
            "license restrictions",
            "chip ban",
            "export ban",
            "trade restriction",
            "trade restrictions",
            "china chip",
        )
        company_action_terms = (
            "cuts",
            "cut",
            "restricts",
            "restricted",
            "tightens",
            "tightened",
            "cannot sell",
            "barred from",
            "blocked from",
            "license",
            "licenses",
            "customer approvals",
            "sales",
            "revenue",
            "shipments",
            "shipping",
        )
        if any(term in text for term in restriction_terms) and any(term in text for term in company_action_terms):
            return "direct_export_control_exposure"

        if any(term in text for term in restriction_terms) or " bis " in f" {text} ":
            return "policy_context"
        return "unrelated"

    @staticmethod
    def _trade_category_weight(category: str) -> float:
        return {
            "direct_sanctions_designation": 1.20,
            "compliance_enforcement_exposure": 1.10,
            "direct_export_control_exposure": 0.90,
            "downstream_diversion_risk": 0.35,
            "policy_context": 0.18,
        }.get(category, 0.0)

    def trade_control_pressure(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        name = self._entity_query_name(entity)
        if not name:
            return {"status": "missing", "score": None, "reason": "missing_company_name"}
        query = f'"{name}" ("export controls" OR "export restrictions" OR sanctions OR "trade restrictions" OR BIS)'
        news = self._fetch_google_news(query, limit=20)
        if news.get("status") != "ok":
            return {"status": "error", "score": None, "source": "Google News RSS", "error": news.get("error")}

        matched: List[Dict[str, Any]] = []
        buckets: Dict[str, int] = {
            "direct_sanctions_designation": 0,
            "compliance_enforcement_exposure": 0,
            "direct_export_control_exposure": 0,
            "downstream_diversion_risk": 0,
            "policy_context": 0,
        }
        weighted_points = 0.0

        for item in news.get("items") or []:
            title = str(item.get("title") or "")
            category = self._trade_control_category(entity, title)
            category_weight = self._trade_category_weight(category)
            if category_weight <= 0:
                continue
            severity = self._severity_from_title(title, cyber=False) or "moderate"
            freshness = self._media_freshness(item.get("published"))
            source_weight = self._source_weight(item.get("source"))
            base_points = 16.0 if severity == "high" else 8.0
            contribution = base_points * freshness * source_weight * category_weight
            weighted_points += contribution
            buckets[category] += 1
            matched.append({
                **dict(item),
                "signal_severity": severity,
                "attribution_category": category,
                "freshness_weight": round(freshness, 2),
                "source_quality_weight": round(source_weight, 2),
                "semantic_weight": round(category_weight, 2),
                "weighted_points": round(contribution, 2),
            })

        if not matched:
            return {
                "status": "screened_no_material_signal",
                "score": None,
                "source": "Google News RSS",
                "query": query,
                "item_count": news.get("count"),
                "signal_buckets": buckets,
                "methodology": self.TRADE_CONTROL_METHODOLOGY,
                "caveat": "No current media signal does not establish zero sanctions or trade-control exposure.",
            }

        score = min(78.0, 8.0 + weighted_points)
        avg_source = sum(float(item["source_quality_weight"]) for item in matched) / len(matched)
        direct_count = (
            buckets["direct_sanctions_designation"]
            + buckets["compliance_enforcement_exposure"]
            + buckets["direct_export_control_exposure"]
        )
        direct_share = direct_count / len(matched)
        confidence = min(92.0, 54.0 + min(len(matched), 8) * 3.0 + avg_source * 10.0 + direct_share * 8.0)

        return {
            "status": "observed",
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "source": "Google News RSS",
            "query": query,
            "item_count": news.get("count"),
            "signal_buckets": buckets,
            "direct_company_signal_count": direct_count,
            "matched_items": matched[:10],
            "methodology": self.TRADE_CONTROL_METHODOLOGY,
            "interpretation": "Company regulatory/trade-control pressure. Direct restrictions and enforcement carry substantially more weight than downstream diversion or general policy context.",
            "caveat": "This is not a legal sanctions determination and does not infer company misconduct from downstream diversion reporting.",
        }

    def cyber_media_pressure(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        result = super().cyber_media_pressure(entity)
        if result.get("status") != "observed":
            return result

        category_counts = {
            "direct_enterprise_incident": 0,
            "product_security": 0,
            "ecosystem_incident": 0,
            "company_context": 0,
        }
        enriched_items: List[Dict[str, Any]] = []
        for item in result.get("matched_items") or []:
            category = self._cyber_context_category(entity, item.get("title"))
            if category in category_counts:
                category_counts[category] += 1
            enriched_items.append({**dict(item), "attribution_category": category})

        result = dict(result)
        result["matched_items"] = enriched_items
        result["attribution_categories"] = category_counts
        result["direct_signal_count"] = category_counts["direct_enterprise_incident"]
        result["product_security_signal_count"] = category_counts["product_security"]
        result["ecosystem_signal_count"] = category_counts["ecosystem_incident"]
        result["methodology"] = self.CYBER_CONTEXT_METHODOLOGY
        result["caveat"] = (
            "Cyber-media context is semantically separated into enterprise incidents, product security, "
            "ecosystem incidents, and general company context; only victim-attributed incidents can become "
            "direct enterprise incident evidence."
        )
        return result

    def enrich(self, *, company_entity_id: str, entity: Mapping[str, Any], edges: List[Mapping[str, Any]]) -> Dict[str, Any]:
        result = super().enrich(company_entity_id=company_entity_id, entity=entity, edges=edges)
        result["methodology"] = "cross_module_dynamic_hazard_enrichment_v6_semantic_evidence_attribution"
        result["operational_calibration_rules"] = [
            "SEC Form 8-K Item 1.05 is the highest-confidence material cyber-incident signal when present.",
            "A company co-mention near breach/cyberattack language is not sufficient for direct-enterprise attribution.",
            "Direct enterprise incidents require victim/affected-entity or self-disclosure attribution syntax.",
            "Cyber-media product-security, ecosystem, and general context are separate from enterprise incident attribution.",
            "NVD product-security pressure is capped at 55 inside Governance / Operational Risk.",
            "General cyber-media context is capped at 35 and receives only a small composite weight.",
            "Product vulnerabilities cannot by themselves create a critical corporate operational score.",
            "Export-control pressure separates direct restrictions/enforcement from downstream diversion and general policy context.",
            "Downstream diversion reporting cannot by itself imply company sanctions non-compliance or misconduct.",
        ]
        result["regulatory_calibration_rules"] = [
            "Direct OFAC designation screening remains separate from export-control media pressure.",
            "Direct company export restrictions and enforcement receive the highest media-evidence weight.",
            "Downstream diversion signals are retained as exposure evidence but heavily down-weighted.",
            "General policy context is retained for awareness but contributes only marginally to company pressure.",
        ]
        return result
