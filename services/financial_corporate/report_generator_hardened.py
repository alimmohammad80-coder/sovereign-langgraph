from __future__ import annotations

from typing import Any, Dict, Mapping

from .report_generator import FinancialCorporateReportGenerator, ReportOptions


class HardenedFinancialCorporateReportGenerator(FinancialCorporateReportGenerator):
    """Production guardrails for evidence-grounded corporate reports.

    Provider/collector failures must remain unknown evidence. They must never be
    translated into a validated zero-signal FACT merely because an error payload
    is a truthy mapping.
    """

    _NVD_SUCCESS_STATUSES = {"observed", "screened_no_recent_published_match"}
    _TRADE_SUCCESS_STATUSES = {"observed", "screened_no_material_signal"}

    def _build_sections(
        self,
        snapshot: Mapping[str, Any],
        registry: Mapping[str, Mapping[str, Any]],
        options: ReportOptions,
    ) -> Dict[str, Any]:
        sections = super()._build_sections(snapshot, registry, options)
        hazards = (snapshot.get("evidence") or {}).get("dynamic_hazards") or {}

        trade = hazards.get("trade_control_pressure") or {}
        if trade and trade.get("status") not in self._TRADE_SUCCESS_STATUSES:
            section = sections.get("sanctions_trade") or {}
            claims = list(section.get("claims") or [])
            # The first claim is the integrated sanctions/trade dimension and
            # OFAC-screening statement. Any later trade-signal count claim is
            # invalid when the media collector itself failed.
            section["claims"] = claims[:1]
            section["summary"] = " ".join(claim.get("text") or "" for claim in section["claims"])
            sections["sanctions_trade"] = section

        nvd = hazards.get("cyber_nvd_pressure") or {}
        if nvd and nvd.get("status") not in self._NVD_SUCCESS_STATUSES:
            section = sections.get("cyber_operational") or {}
            claims = []
            for claim in section.get("claims") or []:
                refs = set(claim.get("evidence_ids") or [])
                if "nvd:product_security" in refs and claim.get("claim_type") == "FACT":
                    continue
                claims.append(claim)
            section["claims"] = claims
            section["summary"] = " ".join(claim.get("text") or "" for claim in claims)
            sections["cyber_operational"] = section

        return sections

    def _evidence_gaps(self, snapshot: Mapping[str, Any]):
        gaps = list(super()._evidence_gaps(snapshot))
        hazards = (snapshot.get("evidence") or {}).get("dynamic_hazards") or {}

        guarded_sources = {
            "trade_control_pressure": hazards.get("trade_control_pressure") or {},
            "cyber_nvd_pressure": hazards.get("cyber_nvd_pressure") or {},
        }
        existing = {
            (gap.get("type"), gap.get("source"), gap.get("error"))
            for gap in gaps
            if isinstance(gap, Mapping)
        }
        for source, payload in guarded_sources.items():
            if not payload or payload.get("status") != "error":
                continue
            error_text = str(payload.get("error") or "collector_failed")
            key = ("collection_error", source, error_text)
            if key in existing:
                continue
            gaps.append(
                {
                    "severity": "material",
                    "type": "collection_error",
                    "source": source,
                    "status": "error",
                    "error": error_text,
                    "interpretation": "Evidence unavailable; no negative screening inference is permitted.",
                }
            )
        return gaps
