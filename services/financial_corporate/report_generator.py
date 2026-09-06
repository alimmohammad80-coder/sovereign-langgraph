from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from html import escape
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


REPORT_METHODOLOGY = "financial_corporate_evidence_grounded_report_v1"


@dataclass(frozen=True)
class ReportOptions:
    report_type: str = "executive_intelligence"
    depth: str = "comprehensive"
    forecast_horizons: Sequence[str] = ("30d", "90d", "180d")
    citation_style: str = "chicago"
    include_methodology: bool = True


class FinancialCorporateReportGenerator:
    """Build an evidence-grounded intelligence report from an integrated snapshot.

    The integrated scoring engine remains authoritative. This service never
    recalculates or replaces source scores; it normalizes evidence, creates
    traceable analytical claims, validates those claims, and renders report
    output suitable for the frontend or export.
    """

    _dimension_labels = {
        "financial_resilience": "Financial Resilience",
        "market_stress": "Market & Credit Stress",
        "supply_chain": "Supply Chain",
        "geopolitical": "Geopolitical",
        "sanctions_compliance": "Sanctions & Trade Controls",
        "governance_operational": "Governance & Operational",
    }

    @staticmethod
    def _num(value: Any) -> Optional[float]:
        try:
            return None if value is None else round(float(value), 2)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _pct(value: Any) -> str:
        number = FinancialCorporateReportGenerator._num(value)
        return "unknown" if number is None else f"{number:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _stable_id(prefix: str, *parts: Any) -> str:
        raw = "|".join(str(part or "") for part in parts)
        return f"{prefix}:{sha1(raw.encode('utf-8')).hexdigest()[:14]}"

    @staticmethod
    def _confidence(values: Iterable[Any], default: float = 60.0) -> float:
        nums = []
        for value in values:
            try:
                if value is not None:
                    nums.append(float(value))
            except (TypeError, ValueError):
                continue
        return round(sum(nums) / len(nums), 2) if nums else default

    def _register(
        self,
        registry: Dict[str, Dict[str, Any]],
        *,
        evidence_id: str,
        source: str,
        title: str,
        url: Optional[str] = None,
        published: Optional[str] = None,
        source_type: str = "source",
        details: Optional[Mapping[str, Any]] = None,
    ) -> str:
        if evidence_id not in registry:
            registry[evidence_id] = {
                "evidence_id": evidence_id,
                "source": source,
                "title": title,
                "url": url,
                "published": published,
                "source_type": source_type,
                "details": dict(details or {}),
            }
        return evidence_id

    def _build_evidence_registry(self, snapshot: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
        registry: Dict[str, Dict[str, Any]] = {}
        evidence = snapshot.get("evidence") or {}

        sec = evidence.get("sec") or {}
        if sec:
            self._register(
                registry,
                evidence_id="sec:companyfacts",
                source=sec.get("source") or "SEC EDGAR/XBRL",
                title=f"Company facts for {sec.get('title') or 'issuer'}",
                url=sec.get("source_url"),
                source_type="authoritative_filing_data",
                details={"cik": sec.get("cik")},
            )

        fundamentals = snapshot.get("fundamentals") or {}
        if fundamentals:
            self._register(
                registry,
                evidence_id="model:fundamentals",
                source="Sovereign Intelligence AI",
                title="Deterministic fundamental-ratio analysis derived from reported observations",
                source_type="derived_analytic",
                details={
                    "methodology": fundamentals.get("methodology"),
                    "evidence_coverage": fundamentals.get("evidence_coverage"),
                    "ratios": fundamentals.get("ratios") or {},
                },
            )

        market_credit = snapshot.get("market_credit") or {}
        if market_credit:
            self._register(
                registry,
                evidence_id="model:market_credit",
                source="Sovereign Intelligence AI",
                title="Market and credit stress composite",
                source_type="derived_analytic",
                details={
                    "methodology": market_credit.get("methodology"),
                    "components": market_credit.get("components") or {},
                    "evidence_coverage": market_credit.get("evidence_coverage"),
                },
            )

        cross_module = evidence.get("cross_module") or {}
        for dimension, rows in (cross_module.get("evidence") or {}).items():
            for index, row in enumerate(rows or []):
                if not isinstance(row, Mapping):
                    continue
                eid = self._stable_id(
                    "cross",
                    dimension,
                    row.get("source_entity_id"),
                    row.get("relationship_type"),
                    index,
                )
                self._register(
                    registry,
                    evidence_id=eid,
                    source=row.get("source_module") or "Sovereign Intelligence AI",
                    title=(
                        f"{dimension} exposure: {row.get('source_entity_id') or 'unresolved source'} "
                        f"via {row.get('relationship_type') or 'relationship'}"
                    ),
                    source_type="cross_module_evidence",
                    details=dict(row),
                )

        hazards = evidence.get("dynamic_hazards") or {}
        country_hazards = hazards.get("country_hazards") or {}
        for iso3, item in country_hazards.items():
            if not isinstance(item, Mapping):
                continue
            self._register(
                registry,
                evidence_id=f"country:{iso3}",
                source=item.get("source") or "Country Intelligence",
                title=f"Latest country risk observation for {iso3}",
                source_type="cross_module_hazard",
                details=dict(item),
            )

        conflict_hazards = hazards.get("conflict_hazards") or {}
        for iso3, item in conflict_hazards.items():
            if not isinstance(item, Mapping):
                continue
            self._register(
                registry,
                evidence_id=f"conflict:{iso3}",
                source=item.get("source") or "Conflict Forecasting",
                title=f"Latest conflict/security hazard for {item.get('country') or iso3}",
                source_type="cross_module_hazard",
                details=dict(item),
            )

        ofac = hazards.get("sanctions_screening") or {}
        if ofac:
            self._register(
                registry,
                evidence_id="ofac:screening",
                source=ofac.get("source") or "U.S. Treasury OFAC",
                title="Direct sanctions designation screening",
                url=ofac.get("source_url"),
                source_type="authoritative_screening",
                details=dict(ofac),
            )

        trade = hazards.get("trade_control_pressure") or {}
        for index, item in enumerate(trade.get("matched_items") or []):
            if not isinstance(item, Mapping):
                continue
            eid = self._stable_id("trade", item.get("title"), item.get("published"), index)
            self._register(
                registry,
                evidence_id=eid,
                source=item.get("source") or trade.get("source") or "Media reporting",
                title=item.get("title") or "Trade-control reporting",
                url=item.get("link"),
                published=item.get("published"),
                source_type="trade_control_reporting",
                details={
                    "attribution_category": item.get("attribution_category"),
                    "semantic_weight": item.get("semantic_weight"),
                    "weighted_points": item.get("weighted_points"),
                },
            )

        sec_cyber = hazards.get("sec_material_cyber_disclosure") or {}
        if sec_cyber:
            self._register(
                registry,
                evidence_id="sec:cyber_item_1_05",
                source=sec_cyber.get("source") or "SEC EDGAR submissions",
                title="SEC Form 8-K Item 1.05 material cybersecurity disclosure screening",
                url=sec_cyber.get("source_url"),
                source_type="authoritative_screening",
                details=dict(sec_cyber),
            )

        direct_cyber = hazards.get("direct_enterprise_cyber_incident") or {}
        for index, item in enumerate(direct_cyber.get("matched_items") or []):
            if not isinstance(item, Mapping):
                continue
            eid = self._stable_id("cyber-enterprise", item.get("title"), item.get("published"), index)
            self._register(
                registry,
                evidence_id=eid,
                source=item.get("source") or direct_cyber.get("source") or "Cyber reporting",
                title=item.get("title") or "Enterprise cyber incident reporting",
                url=item.get("link"),
                published=item.get("published"),
                source_type="enterprise_cyber_reporting",
                details={"attribution_category": item.get("attribution_category")},
            )

        nvd = hazards.get("cyber_nvd_pressure") or {}
        if nvd:
            self._register(
                registry,
                evidence_id="nvd:product_security",
                source=nvd.get("source") or "NIST National Vulnerability Database",
                title="Recent product-security vulnerability evidence",
                url=nvd.get("source_url"),
                source_type="authoritative_vulnerability_data",
                details={
                    "matched_count": nvd.get("matched_count"),
                    "max_cvss_base_score": nvd.get("max_cvss_base_score"),
                    "average_cvss_base_score": nvd.get("average_cvss_base_score"),
                    "lookback_days": nvd.get("lookback_days"),
                },
            )

        cyber_media = hazards.get("cyber_media_pressure") or {}
        for index, item in enumerate(cyber_media.get("matched_items") or []):
            if not isinstance(item, Mapping):
                continue
            eid = self._stable_id("cyber-context", item.get("title"), item.get("published"), index)
            self._register(
                registry,
                evidence_id=eid,
                source=item.get("source") or cyber_media.get("source") or "Cyber reporting",
                title=item.get("title") or "Cyber context reporting",
                url=item.get("link"),
                published=item.get("published"),
                source_type=f"cyber_{item.get('attribution_category') or 'context'}",
                details={"attribution_category": item.get("attribution_category")},
            )

        self._register(
            registry,
            evidence_id="model:integrated_risk",
            source="Sovereign Intelligence AI",
            title="Integrated deterministic corporate risk assessment",
            source_type="derived_analytic",
            details={
                "methodology": (snapshot.get("overall") or {}).get("methodology"),
                "snapshot_methodology": snapshot.get("methodology"),
                "ai_generated_score": snapshot.get("ai_generated_score", False),
            },
        )
        return registry

    @staticmethod
    def _claim(
        claim_type: str,
        text: str,
        confidence: float,
        evidence_ids: Sequence[str],
        *,
        horizon: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "claim_type": claim_type,
            "text": text,
            "confidence": round(float(confidence), 2),
            "evidence_ids": list(dict.fromkeys(evidence_ids)),
            "horizon": horizon,
        }

    def _eids_by_dimension(self, registry: Mapping[str, Mapping[str, Any]], dimension: str) -> List[str]:
        found = []
        for eid, item in registry.items():
            details = item.get("details") or {}
            title = str(item.get("title") or "").lower()
            if dimension in title or details.get("dimension") == dimension:
                found.append(eid)
        return found

    def _build_sections(
        self,
        snapshot: Mapping[str, Any],
        registry: Mapping[str, Mapping[str, Any]],
        options: ReportOptions,
    ) -> Dict[str, Any]:
        entity = snapshot.get("entity") or {}
        name = entity.get("common_name") or entity.get("legal_name") or "The company"
        overall = snapshot.get("overall") or {}
        dimensions = overall.get("dimensions") or {}
        dimension_conf = overall.get("dimension_confidence") or {}
        fundamentals = snapshot.get("fundamentals") or {}
        market = snapshot.get("market_credit") or {}
        distress = snapshot.get("distress") or {}
        hazards = (snapshot.get("evidence") or {}).get("dynamic_hazards") or {}

        sections: Dict[str, Any] = {}

        overall_eids = ["model:integrated_risk"]
        overall_claims = [
            self._claim(
                "FACT",
                f"{name} has an integrated corporate risk score of {self._pct(overall.get('overall_risk_score'))}/100, "
                f"classified as {overall.get('risk_level') or 'Unclassified'}, with evidence confidence of "
                f"{self._pct(overall.get('confidence_score'))}%.",
                self._num(overall.get("confidence_score")) or 0.0,
                overall_eids,
            )
        ]
        for driver in overall.get("top_drivers") or []:
            dimension = driver.get("dimension")
            label = self._dimension_labels.get(dimension, str(dimension).replace("_", " ").title())
            eids = self._eids_by_dimension(registry, str(dimension)) or ["model:integrated_risk"]
            overall_claims.append(
                self._claim(
                    "JUDGMENT",
                    f"{label} is a principal contributor to integrated risk, with a dimension score of "
                    f"{self._pct(driver.get('score'))}/100 and weighted contribution of "
                    f"{self._pct(driver.get('weighted_contribution'))} points.",
                    self._num(dimension_conf.get(dimension)) or 60.0,
                    eids,
                )
            )
        sections["overall_assessment"] = {
            "title": "Overall Risk Assessment",
            "summary": overall_claims[0]["text"],
            "claims": overall_claims,
            "data": {
                "risk_score": overall.get("overall_risk_score"),
                "risk_level": overall.get("risk_level"),
                "confidence": overall.get("confidence_score"),
                "assessment_status": overall.get("assessment_status"),
                "dimensions": dimensions,
                "dimension_confidence": dimension_conf,
            },
        }

        ratios = fundamentals.get("ratios") or {}
        financial_eids = [eid for eid in ("sec:companyfacts", "model:fundamentals", "model:market_credit") if eid in registry]
        financial_claims = []
        if fundamentals:
            financial_claims.append(
                self._claim(
                    "FACT",
                    f"Financial-resilience risk is {self._pct(dimensions.get('financial_resilience'))}/100. "
                    f"Reported-observation analysis shows a current ratio of {self._pct(ratios.get('current_ratio'))}, "
                    f"debt-to-equity of {self._pct(ratios.get('debt_to_equity'))}, and net margin of "
                    f"{self._pct(ratios.get('net_margin'))}.",
                    self._num(dimension_conf.get("financial_resilience")) or 0.0,
                    financial_eids,
                )
            )
        financial_claims.append(
            self._claim(
                "FACT",
                f"The distress screening score is {self._pct(distress.get('distress_score'))}/100 "
                f"({distress.get('distress_level') or 'Unclassified'}), while market-credit stress is "
                f"{self._pct(market.get('market_credit_stress_score'))}/100.",
                self._confidence([distress.get("confidence_score"), market.get("confidence_score")]),
                financial_eids or ["model:integrated_risk"],
            )
        )
        sections["financial_resilience"] = {
            "title": "Financial Resilience & Distress",
            "summary": " ".join(claim["text"] for claim in financial_claims),
            "claims": financial_claims,
            "data": {"ratios": ratios, "distress": distress, "market_credit": market},
        }

        supply_eids = [eid for eid, item in registry.items() if item.get("source_type") == "cross_module_evidence" and "supply_chain" in str(item.get("title"))]
        supply_score = dimensions.get("supply_chain")
        supply_claims = [
            self._claim(
                "JUDGMENT",
                f"Supply-chain risk is {self._pct(supply_score)}/100 with {self._pct(dimension_conf.get('supply_chain'))}% evidence confidence. "
                "The score reflects structural exposure combined with dynamic hazard and evidence confidence rather than media volume alone.",
                self._num(dimension_conf.get("supply_chain")) or 0.0,
                supply_eids or ["model:integrated_risk"],
            )
        ]
        sections["supply_chain"] = {
            "title": "Supply Chain Exposure",
            "summary": supply_claims[0]["text"],
            "claims": supply_claims,
            "data": {"score": supply_score, "evidence_confidence": dimension_conf.get("supply_chain")},
        }

        geo_eids = [eid for eid in registry if eid.startswith("country:") or eid.startswith("conflict:")]
        geopolitical_claims = [
            self._claim(
                "JUDGMENT",
                f"Geopolitical risk is {self._pct(dimensions.get('geopolitical'))}/100 with "
                f"{self._pct(dimension_conf.get('geopolitical'))}% evidence confidence. The assessment reflects company exposure "
                "to country and conflict hazards and should be read separately from a probability of conflict.",
                self._num(dimension_conf.get("geopolitical")) or 0.0,
                geo_eids or ["model:integrated_risk"],
            )
        ]
        sections["geopolitical"] = {
            "title": "Geopolitical Exposure",
            "summary": geopolitical_claims[0]["text"],
            "claims": geopolitical_claims,
            "data": {
                "score": dimensions.get("geopolitical"),
                "country_hazards": hazards.get("country_hazards") or {},
                "conflict_hazards": hazards.get("conflict_hazards") or {},
            },
        }

        trade_eids = [eid for eid in registry if eid.startswith("trade:")]
        sanctions_eids = (["ofac:screening"] if "ofac:screening" in registry else []) + trade_eids
        ofac = hazards.get("sanctions_screening") or {}
        trade = hazards.get("trade_control_pressure") or {}
        sanctions_claims = [
            self._claim(
                "FACT",
                f"Sanctions and trade-control risk is {self._pct(dimensions.get('sanctions_compliance'))}/100. "
                f"Direct OFAC screening status is '{ofac.get('status') or 'not available'}'; this screening result does not establish zero sanctions or export-control risk.",
                self._num(dimension_conf.get("sanctions_compliance")) or 0.0,
                sanctions_eids or ["model:integrated_risk"],
            )
        ]
        if trade:
            buckets = trade.get("signal_buckets") or {}
            sanctions_claims.append(
                self._claim(
                    "JUDGMENT",
                    f"Trade-control reporting contains {buckets.get('direct_export_control_exposure', 0)} direct export-control signal(s), "
                    f"{buckets.get('compliance_enforcement_exposure', 0)} enforcement-exposure signal(s), and "
                    f"{buckets.get('downstream_diversion_risk', 0)} downstream-diversion signal(s). Downstream diversion is treated as exposure evidence, not evidence of company misconduct.",
                    self._num(trade.get("confidence")) or self._num(dimension_conf.get("sanctions_compliance")) or 60.0,
                    trade_eids or sanctions_eids or ["model:integrated_risk"],
                )
            )
        sections["sanctions_trade"] = {
            "title": "Sanctions & Trade Controls",
            "summary": " ".join(claim["text"] for claim in sanctions_claims),
            "claims": sanctions_claims,
            "data": {"score": dimensions.get("sanctions_compliance"), "ofac": ofac, "trade_control": trade},
        }

        cyber_eids = [eid for eid in registry if eid.startswith("cyber-enterprise:")]
        cyber_support = cyber_eids + [eid for eid in ("sec:cyber_item_1_05", "nvd:product_security") if eid in registry]
        direct = hazards.get("direct_enterprise_cyber_incident") or {}
        nvd = hazards.get("cyber_nvd_pressure") or {}
        cyber_claims = [
            self._claim(
                "JUDGMENT",
                f"Governance and operational risk is {self._pct(dimensions.get('governance_operational'))}/100 with "
                f"{self._pct(dimension_conf.get('governance_operational'))}% evidence confidence. Enterprise incidents, product vulnerabilities, "
                "and ecosystem context are kept analytically separate.",
                self._num(dimension_conf.get("governance_operational")) or 0.0,
                cyber_support or ["model:integrated_risk"],
            )
        ]
        if direct.get("status") == "observed":
            cyber_claims.append(
                self._claim(
                    "FACT",
                    f"Victim-attributed reporting identifies {direct.get('matched_count') or 0} direct enterprise cyber incident signal(s); "
                    "company co-mentions alone are excluded from direct-enterprise attribution.",
                    self._num(direct.get("confidence")) or 60.0,
                    cyber_eids,
                )
            )
        if nvd:
            cyber_claims.append(
                self._claim(
                    "FACT",
                    f"NVD product-security evidence includes {nvd.get('matched_count') or 0} recently published matched vulnerabilities, "
                    f"with maximum observed CVSS base score {self._pct(nvd.get('max_cvss_base_score'))}; product-security pressure is capped inside the corporate operational composite.",
                    self._num(nvd.get("confidence")) or 60.0,
                    ["nvd:product_security"],
                )
            )
        sections["cyber_operational"] = {
            "title": "Cyber & Operational Risk",
            "summary": " ".join(claim["text"] for claim in cyber_claims),
            "claims": cyber_claims,
            "data": {
                "score": dimensions.get("governance_operational"),
                "direct_enterprise_incident": direct,
                "product_security": nvd,
                "sec_material_cyber": hazards.get("sec_material_cyber_disclosure") or {},
            },
        }

        driver_names = [self._dimension_labels.get(item.get("dimension"), str(item.get("dimension"))) for item in overall.get("top_drivers") or []]
        outlook_claims = []
        for horizon in options.forecast_horizons:
            outlook_claims.append(
                self._claim(
                    "FORECAST",
                    f"Over the {horizon} horizon, the directional risk outlook remains primarily sensitive to "
                    f"{', '.join(driver_names) if driver_names else 'the currently observed risk drivers'}. This is an indicator-based directional outlook, not a calibrated event probability.",
                    self._num(overall.get("confidence_score")) or 0.0,
                    ["model:integrated_risk"] + geo_eids + supply_eids,
                    horizon=horizon,
                )
            )
        sections["outlook"] = {
            "title": "Directional Outlook & Indicators",
            "summary": " ".join(claim["text"] for claim in outlook_claims),
            "claims": outlook_claims,
            "data": {"horizons": list(options.forecast_horizons), "calibrated_probability": False},
        }
        return sections

    def _evidence_gaps(self, snapshot: Mapping[str, Any]) -> List[Dict[str, Any]]:
        gaps: List[Dict[str, Any]] = []
        overall = snapshot.get("overall") or {}
        for dimension in overall.get("missing_dimensions") or []:
            gaps.append({"severity": "material", "type": "missing_dimension", "dimension": dimension})

        hazards = (snapshot.get("evidence") or {}).get("dynamic_hazards") or {}
        for iso3, item in (hazards.get("country_hazards") or {}).items():
            freshness = (item or {}).get("freshness") or {}
            status = freshness.get("freshness_status")
            if status in {"aging", "stale"}:
                gaps.append({
                    "severity": "moderate" if status == "aging" else "material",
                    "type": "aging_evidence",
                    "source": f"country:{iso3}",
                    "age_days": freshness.get("age_days"),
                    "freshness_status": status,
                })

        for error in (snapshot.get("evidence") or {}).get("collection_errors") or []:
            gaps.append({"severity": "moderate", "type": "collection_error", **dict(error)})
        return gaps

    def _indicators(self, snapshot: Mapping[str, Any]) -> List[Dict[str, Any]]:
        overall = snapshot.get("overall") or {}
        indicators = []
        for driver in overall.get("top_drivers") or []:
            dimension = driver.get("dimension")
            indicators.append({
                "dimension": dimension,
                "current_score": driver.get("score"),
                "watch_for": {
                    "supply_chain": "Changes in exposed-country conflict intensity, supplier concentration, facility or chokepoint disruption.",
                    "geopolitical": "Material change in country risk, conflict escalation, trade restrictions, or coercive policy action.",
                    "governance_operational": "New victim-attributed enterprise incidents, material SEC Item 1.05 disclosures, or significant operational disruption.",
                    "sanctions_compliance": "Direct designation, enforcement action, or company-specific export-control restrictions.",
                    "market_stress": "Sustained equity drawdown, volatility expansion, or deterioration in system credit conditions.",
                    "financial_resilience": "Deterioration in liquidity, leverage, margins, debt service, or cash-flow coverage.",
                }.get(dimension, "Material change in the evidence underlying this risk dimension."),
            })
        return indicators

    def _key_judgments(self, sections: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
        selected = []
        for key in ("overall_assessment", "supply_chain", "geopolitical", "sanctions_trade", "cyber_operational"):
            claims = (sections.get(key) or {}).get("claims") or []
            if claims:
                selected.append(claims[0])
        return selected

    def _validate_claims(
        self,
        sections: Mapping[str, Mapping[str, Any]],
        registry: Mapping[str, Mapping[str, Any]],
    ) -> Dict[str, Any]:
        errors = []
        count = 0
        for section_key, section in sections.items():
            for index, claim in enumerate(section.get("claims") or []):
                count += 1
                claim_type = claim.get("claim_type")
                refs = claim.get("evidence_ids") or []
                if claim_type in {"FACT", "JUDGMENT", "FORECAST"} and not refs:
                    errors.append({"section": section_key, "claim": index, "error": "missing_evidence_reference"})
                for evidence_id in refs:
                    if evidence_id not in registry:
                        errors.append({
                            "section": section_key,
                            "claim": index,
                            "error": "dangling_evidence_reference",
                            "evidence_id": evidence_id,
                        })
                if claim_type == "FORECAST" and not claim.get("horizon"):
                    errors.append({"section": section_key, "claim": index, "error": "forecast_missing_horizon"})
        return {"status": "pass" if not errors else "fail", "claim_count": count, "errors": errors}

    def _citation_notes(self, registry: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
        notes = []
        for index, (evidence_id, item) in enumerate(registry.items(), start=1):
            source = item.get("source") or "Unknown source"
            title = item.get("title") or "Untitled evidence"
            published = item.get("published")
            url = item.get("url")
            parts = [f"{source}, “{title}”"]
            if published:
                parts.append(str(published))
            if url:
                parts.append(str(url))
            note = ", ".join(parts) + "."
            notes.append({"number": index, "evidence_id": evidence_id, "note": note})
        return notes

    def generate(self, snapshot: Mapping[str, Any], options: Optional[ReportOptions] = None) -> Dict[str, Any]:
        options = options or ReportOptions()
        registry = self._build_evidence_registry(snapshot)
        sections = self._build_sections(snapshot, registry, options)
        validation = self._validate_claims(sections, registry)
        if validation["status"] != "pass":
            raise ValueError(f"Report claim validation failed: {validation['errors']}")

        overall = snapshot.get("overall") or {}
        entity = snapshot.get("entity") or {}
        name = entity.get("common_name") or entity.get("legal_name") or "Company"
        key_judgments = self._key_judgments(sections)
        drivers = [
            self._dimension_labels.get(item.get("dimension"), str(item.get("dimension")))
            for item in overall.get("top_drivers") or []
        ]
        bluf = (
            f"{name} is assessed at {self._pct(overall.get('overall_risk_score'))}/100 "
            f"({overall.get('risk_level') or 'Unclassified'}) with {self._pct(overall.get('confidence_score'))}% evidence confidence. "
            f"The principal integrated risk drivers are {', '.join(drivers) if drivers else 'not yet sufficiently resolved'}. "
            "The assessment preserves deterministic source scores and separates structural exposure from dynamic hazard, direct sanctions screening from trade-control pressure, and enterprise cyber incidents from product or ecosystem security context. "
            "Directional outlooks identify conditions to monitor and are not calibrated event probabilities."
        )

        return {
            "report_schema_version": "1.0",
            "report_type": options.report_type,
            "depth": options.depth,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entity": dict(entity),
            "assessment": {
                "risk_score": overall.get("overall_risk_score"),
                "risk_level": overall.get("risk_level"),
                "confidence": overall.get("confidence_score"),
                "assessment_status": overall.get("assessment_status"),
                "dimension_confidence": overall.get("dimension_confidence") or {},
                "score_authority": "integrated_snapshot",
                "ai_generated_score": False,
            },
            "bluf": bluf,
            "key_judgments": key_judgments,
            "sections": sections,
            "indicators_to_watch": self._indicators(snapshot),
            "evidence_gaps": self._evidence_gaps(snapshot),
            "evidence_registry": list(registry.values()),
            "citations": self._citation_notes(registry),
            "claim_validation": validation,
            "methodology": {
                "report_generation": REPORT_METHODOLOGY,
                "source_snapshot_methodology": snapshot.get("methodology"),
                "citation_style": options.citation_style,
                "scoring_policy": "The report generator does not create, modify, or override risk scores.",
                "claim_policy": {
                    "FACT": "Requires direct evidence reference.",
                    "JUDGMENT": "Requires supporting evidence reference and explicit evidence confidence.",
                    "FORECAST": "Requires horizon, supporting drivers/evidence, and is not a calibrated probability unless explicitly stated.",
                    "UNKNOWN": "Must remain an explicit evidence gap.",
                    "NO_MATCH": "Must not be translated into zero risk.",
                },
            } if options.include_methodology else None,
        }

    @staticmethod
    def _citation_number_map(report: Mapping[str, Any]) -> Dict[str, int]:
        return {item["evidence_id"]: item["number"] for item in report.get("citations") or []}

    def render_markdown(self, report: Mapping[str, Any]) -> str:
        entity = report.get("entity") or {}
        name = entity.get("common_name") or entity.get("legal_name") or "Company"
        citation_map = self._citation_number_map(report)

        def refs(claim: Mapping[str, Any]) -> str:
            nums = [citation_map[eid] for eid in claim.get("evidence_ids") or [] if eid in citation_map]
            return "" if not nums else " " + "".join(f"[{n}]" for n in nums)

        lines = [
            f"# {name} — Financial & Corporate Risk Intelligence Report",
            "",
            f"**Generated:** {report.get('generated_at')}",
            f"**Overall risk:** {report.get('assessment', {}).get('risk_score')}/100 ({report.get('assessment', {}).get('risk_level')})",
            f"**Evidence confidence:** {report.get('assessment', {}).get('confidence')}%",
            "",
            "## BLUF",
            report.get("bluf") or "",
            "",
        ]
        for section in (report.get("sections") or {}).values():
            lines.extend([f"## {section.get('title')}", ""])
            for claim in section.get("claims") or []:
                lines.append(f"- {claim.get('text')}{refs(claim)}")
            lines.append("")

        gaps = report.get("evidence_gaps") or []
        lines.extend(["## Analytic Confidence & Evidence Gaps", ""])
        if gaps:
            for gap in gaps:
                lines.append(f"- {gap.get('type')}: {gap}")
        else:
            lines.append("- No material evidence gaps were identified by the report validator.")
        lines.extend(["", "## Notes / Sources", ""])
        for citation in report.get("citations") or []:
            lines.append(f"[{citation.get('number')}] {citation.get('note')}")
        return "\n".join(lines).strip() + "\n"

    def render_html(self, report: Mapping[str, Any]) -> str:
        markdown = self.render_markdown(report)
        # Deliberately dependency-free HTML renderer for backend portability.
        blocks = []
        in_list = False
        for raw in markdown.splitlines():
            line = raw.rstrip()
            if line.startswith("# "):
                if in_list:
                    blocks.append("</ul>")
                    in_list = False
                blocks.append(f"<h1>{escape(line[2:])}</h1>")
            elif line.startswith("## "):
                if in_list:
                    blocks.append("</ul>")
                    in_list = False
                blocks.append(f"<h2>{escape(line[3:])}</h2>")
            elif line.startswith("- "):
                if not in_list:
                    blocks.append("<ul>")
                    in_list = True
                blocks.append(f"<li>{escape(line[2:])}</li>")
            elif line:
                if in_list:
                    blocks.append("</ul>")
                    in_list = False
                blocks.append(f"<p>{escape(line)}</p>")
        if in_list:
            blocks.append("</ul>")
        return "<!doctype html><html><head><meta charset=\"utf-8\"><title>Corporate Intelligence Report</title></head><body>" + "".join(blocks) + "</body></html>"
