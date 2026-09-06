from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Optional

from services.supabase_client import get_supabase_client
from .entity_master import CorporateEntityMaster


class CrossModuleEvidenceRepository:
    """Read and normalize cross-module evidence from existing Supabase tables.

    The repository deliberately adapts to the platform's existing schema rather
    than creating duplicate Financial/Corporate tables. Missing or incompatible
    records are surfaced as diagnostics and are never converted into fabricated
    risk evidence.
    """

    DEFAULT_TABLES = {
        "supply_chain": [
            "sc_company_exposure",
            "supply_chain_company_exposures",
            "supply_chain_exposures",
            "supply_chain_risk_scores",
        ],
        "country": [
            "corporate_exposures",
            "corporate_country_exposures",
            "country_corporate_exposures",
        ],
        "conflict": [
            "corporate_exposures",
            "corporate_conflict_exposures",
            "conflict_corporate_exposures",
        ],
        "sanctions": [
            "corporate_exposures",
            "corporate_sanctions_exposures",
            "sanctions_corporate_exposures",
        ],
        "cyber": [
            "corporate_exposures",
            "corporate_cyber_exposures",
            "cyber_corporate_exposures",
        ],
    }

    ENV_KEYS = {
        "supply_chain": "FINCORP_SUPPLY_CHAIN_EXPOSURE_TABLE",
        "country": "FINCORP_COUNTRY_EXPOSURE_TABLE",
        "conflict": "FINCORP_CONFLICT_EXPOSURE_TABLE",
        "sanctions": "FINCORP_SANCTIONS_EXPOSURE_TABLE",
        "cyber": "FINCORP_CYBER_EXPOSURE_TABLE",
    }

    MODULE_ALIASES = {
        "supply_chain": {"supply_chain", "supply-chain", "supply chain", "logistics", "supplier"},
        "country": {"country", "country_risk", "country risk", "geopolitical", "geo", "political"},
        "conflict": {"conflict", "conflict_forecasting", "conflict forecasting", "war", "security"},
        "sanctions": {"sanctions", "sanction", "trade", "trade_controls", "export_control", "export controls"},
        "cyber": {"cyber", "cybersecurity", "information_ops", "information operations", "operational"},
    }

    COMPANY_REFERENCE_KEYS = (
        "company_entity_id",
        "target_entity_id",
        "company_id",
        "corporate_entity_id",
        "ticker",
        "symbol",
        "company_ticker",
        "company_name",
        "company",
    )

    MODULE_DISCRIMINATOR_KEYS = (
        "module",
        "source_module",
        "domain",
        "risk_domain",
        "risk_type",
        "exposure_type",
        "category",
        "type",
    )

    CRITICALITY_SCORES = {
        "none": 0.0,
        "minimal": 10.0,
        "low": 25.0,
        "guarded": 35.0,
        "moderate": 50.0,
        "medium": 50.0,
        "elevated": 60.0,
        "high": 75.0,
        "severe": 85.0,
        "critical": 95.0,
    }

    def __init__(self, client=None) -> None:
        self.client = client
        self.entity_master = CorporateEntityMaster()

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
    def _available_columns(rows: List[Mapping[str, Any]], cap: int = 80) -> List[str]:
        columns = set()
        for row in rows[:25]:
            columns.update(str(key) for key in row.keys())
        return sorted(columns)[:cap]

    @staticmethod
    def _sample_values(rows: List[Mapping[str, Any]], keys: List[str], cap: int = 10) -> Dict[str, List[str]]:
        samples: Dict[str, List[str]] = {}
        for key in keys:
            values: List[str] = []
            seen = set()
            for row in rows[:100]:
                raw = row.get(key)
                if raw is None:
                    continue
                value = str(raw).strip()
                if not value or value in seen:
                    continue
                seen.add(value)
                values.append(value)
                if len(values) >= cap:
                    break
            if values:
                samples[key] = values
        return samples

    @classmethod
    def _criticality_score(cls, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = None
        if number is not None:
            if 0.0 <= number <= 1.0:
                number *= 100.0
            return max(0.0, min(100.0, number))
        text = str(value).strip().lower()
        if not text:
            return None
        return cls.CRITICALITY_SCORES.get(text)

    def _resolve_company_entity_id(self, row: Mapping[str, Any]) -> Optional[str]:
        for key in self.COMPANY_REFERENCE_KEYS:
            raw = row.get(key)
            if raw is None:
                continue
            reference = str(raw).strip()
            if not reference:
                continue
            if reference.startswith("corp_"):
                return reference
            try:
                resolved = self.entity_master.resolve(reference)
            except Exception:
                resolved = None
            if isinstance(resolved, Mapping) and resolved.get("entity_id"):
                return str(resolved["entity_id"])
        return None

    def _row_matches_module(self, module: str, row: Mapping[str, Any], table: str) -> bool:
        if table != "corporate_exposures":
            return True

        discriminator_values: List[str] = []
        for key in self.MODULE_DISCRIMINATOR_KEYS:
            value = row.get(key)
            if value is not None and str(value).strip():
                discriminator_values.append(str(value).strip().lower())

        if not discriminator_values:
            return False

        aliases = self.MODULE_ALIASES[module]
        for value in discriminator_values:
            if value in aliases:
                return True
            if any(alias in value for alias in aliases):
                return True
        return False

    def _normalize_row(self, module: str, row: Mapping[str, Any], table: str) -> Optional[Dict[str, Any]]:
        if not self._row_matches_module(module, row, table):
            return None

        normalized = dict(row)
        company_entity_id = self._resolve_company_entity_id(normalized)
        if not company_entity_id:
            return None
        normalized["company_entity_id"] = company_entity_id

        if module == "country":
            normalized.setdefault(
                "country_iso3",
                normalized.get("country_code") or normalized.get("iso3"),
            )
            if normalized.get("country_iso3") is None and normalized.get("country_id") is not None:
                normalized["country_entity_id"] = str(normalized.get("country_id"))
        elif module == "conflict":
            normalized.setdefault("conflict_id", normalized.get("event_id") or normalized.get("scenario_id"))
        elif module == "sanctions":
            normalized.setdefault(
                "counterparty_entity_id",
                normalized.get("sanctioned_entity_id") or normalized.get("counterparty_id") or normalized.get("source_entity_id"),
            )
        elif module == "cyber":
            normalized.setdefault(
                "incident_id",
                normalized.get("cyber_incident_id") or normalized.get("campaign_id") or normalized.get("event_id") or normalized.get("source_entity_id"),
            )
        elif module == "supply_chain":
            commodity_code = normalized.get("commodity_code")
            commodity_name = normalized.get("commodity_name")
            supplier_country = normalized.get("supplier_country")
            dependency_id = (
                normalized.get("dependency_id")
                or normalized.get("supplier_id")
                or normalized.get("supplier_entity_id")
                or normalized.get("facility_id")
                or normalized.get("port_id")
                or normalized.get("chokepoint_id")
                or normalized.get("commodity_id")
                or normalized.get("source_entity_id")
            )
            if not dependency_id and commodity_code:
                dependency_id = f"commodity:{commodity_code}"
            if not dependency_id and commodity_name:
                dependency_id = f"commodity:{str(commodity_name).strip().lower().replace(' ', '_')}"
            if not dependency_id and supplier_country:
                dependency_id = f"country:{str(supplier_country).strip()}"
            if dependency_id:
                normalized["dependency_entity_id"] = str(dependency_id)

            if normalized.get("dependency_share") is None:
                normalized["dependency_share"] = (
                    normalized.get("dependency_pct")
                    if normalized.get("dependency_pct") is not None
                    else normalized.get("exposure_share")
                    or normalized.get("share")
                    or normalized.get("weight")
                )

            if normalized.get("severity_score") is None and normalized.get("risk_score") is None:
                criticality_score = self._criticality_score(normalized.get("criticality"))
                if criticality_score is not None:
                    normalized["severity_score"] = criticality_score
                    normalized["severity_source"] = "stored_criticality_category"

            normalized.setdefault("relationship_type", "commodity_dependency")
            normalized.setdefault("confidence", 75.0)

        return normalized

    @staticmethod
    def _compatible(module: str, row: Mapping[str, Any]) -> bool:
        if not row.get("company_entity_id"):
            return False
        module_keys = {
            "supply_chain": ["dependency_entity_id", "supplier_entity_id", "facility_id", "port_id", "chokepoint_id", "commodity_id", "source_entity_id"],
            "country": ["country_iso3", "country_entity_id", "iso3", "country_code"],
            "conflict": ["conflict_id", "scenario_id", "event_id", "source_entity_id"],
            "sanctions": ["counterparty_entity_id", "sanctioned_entity_id", "counterparty_id", "source_entity_id"],
            "cyber": ["incident_id", "cyber_incident_id", "campaign_id", "actor_id", "event_id", "source_entity_id"],
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

            normalized_rows: List[Dict[str, Any]] = []
            module_match_count = 0
            for row in rows:
                if self._row_matches_module(module, row, table):
                    module_match_count += 1
                normalized = self._normalize_row(module, row, table)
                if normalized is not None and self._compatible(module, normalized):
                    normalized_rows.append(normalized)

            diagnostic: Dict[str, Any] = {
                "table": table,
                "status": "ok",
                "row_count": len(rows),
                "module_match_count": module_match_count,
                "compatible_row_count": len(normalized_rows),
            }
            if rows:
                diagnostic["available_columns"] = self._available_columns(rows)
                samples = self._sample_values(
                    rows,
                    [
                        "company_name",
                        "company_id",
                        "country_id",
                        "exposure_type",
                        "exposure_level",
                        "criticality",
                        "dependency_pct",
                    ],
                )
                if samples:
                    diagnostic["sample_values"] = samples
            diagnostics.append(diagnostic)

            if normalized_rows:
                return {
                    "module": module,
                    "table": table,
                    "rows": normalized_rows,
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
            "rule": "Existing platform tables are adapted in place. Only explicitly compatible records are ingested; absent relationships or severity are not inferred.",
        }
