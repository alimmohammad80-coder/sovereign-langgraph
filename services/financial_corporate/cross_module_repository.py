from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Optional

from services.supabase_client import get_supabase_client


class CrossModuleEvidenceRepository:
    """Read cross-module evidence from Supabase without coupling to one table layout.

    Table names can be overridden with environment variables. Missing tables are
    reported as diagnostics and never converted into fabricated evidence.
    """

    DEFAULT_TABLES = {
        "supply_chain": ["supply_chain_company_exposures", "supply_chain_exposures", "supply_chain_risk_scores"],
        "country": ["corporate_country_exposures", "country_corporate_exposures"],
        "conflict": ["corporate_conflict_exposures", "conflict_corporate_exposures"],
        "sanctions": ["corporate_sanctions_exposures", "sanctions_corporate_exposures"],
        "cyber": ["corporate_cyber_exposures", "cyber_corporate_exposures"],
    }

    ENV_KEYS = {
        "supply_chain": "FINCORP_SUPPLY_CHAIN_EXPOSURE_TABLE",
        "country": "FINCORP_COUNTRY_EXPOSURE_TABLE",
        "conflict": "FINCORP_CONFLICT_EXPOSURE_TABLE",
        "sanctions": "FINCORP_SANCTIONS_EXPOSURE_TABLE",
        "cyber": "FINCORP_CYBER_EXPOSURE_TABLE",
    }

    def __init__(self, client=None) -> None:
        self.client = client

    def _client(self):
        if self.client is not None:
            return self.client
        return get_supabase_client()

    def candidate_tables(self, module: str) -> List[str]:
        override = (os.getenv(self.ENV_KEYS[module]) or "").strip()
        if override:
            return [override]
        return list(self.DEFAULT_TABLES[module])

    def _fetch_table(self, table: str, limit: int) -> List[Dict[str, Any]]:
        response = self._client().table(table).select("*").limit(limit).execute()
        data = getattr(response, "data", None) or []
        return [dict(row) for row in data if isinstance(row, Mapping)]

    @staticmethod
    def _compatible(module: str, row: Mapping[str, Any]) -> bool:
        company_present = bool(row.get("company_entity_id") or row.get("target_entity_id"))
        if not company_present:
            return False
        module_keys = {
            "supply_chain": ["dependency_entity_id", "supplier_entity_id", "facility_id", "port_id", "chokepoint_id", "commodity_id", "source_entity_id"],
            "country": ["country_iso3", "iso3"],
            "conflict": ["conflict_id", "scenario_id", "source_entity_id"],
            "sanctions": ["counterparty_entity_id", "sanctioned_entity_id", "source_entity_id"],
            "cyber": ["incident_id", "campaign_id", "actor_id", "source_entity_id"],
        }
        return any(row.get(key) for key in module_keys[module])

    def collect_module(self, module: str, limit: int = 1000) -> Dict[str, Any]:
        diagnostics: List[Dict[str, Any]] = []
        for table in self.candidate_tables(module):
            try:
                rows = self._fetch_table(table, limit)
            except Exception as exc:
                diagnostics.append({"table": table, "status": "unavailable", "detail": str(exc)[:240]})
                continue

            compatible = [row for row in rows if self._compatible(module, row)]
            diagnostics.append({
                "table": table,
                "status": "ok",
                "row_count": len(rows),
                "compatible_row_count": len(compatible),
            })
            if compatible:
                return {
                    "module": module,
                    "table": table,
                    "rows": compatible,
                    "diagnostics": diagnostics,
                }

        return {"module": module, "table": None, "rows": [], "diagnostics": diagnostics}

    def collect_all(self, limit_per_module: int = 1000) -> Dict[str, Any]:
        payloads: Dict[str, List[Dict[str, Any]]] = {}
        diagnostics: Dict[str, Any] = {}
        for module in self.DEFAULT_TABLES:
            result = self.collect_module(module, limit=limit_per_module)
            payloads[module] = result["rows"]
            diagnostics[module] = {
                "selected_table": result["table"],
                "attempts": result["diagnostics"],
            }
        return {
            "payloads": payloads,
            "diagnostics": diagnostics,
            "rule": "Only explicitly compatible stored exposure records are ingested; absent relationships are not inferred.",
        }
