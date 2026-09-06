from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Optional

from services.supabase_client import get_supabase_client
from .entity_master import CorporateEntityMaster


class CrossModuleEvidenceRepository:
    """Read and normalize cross-module evidence from existing Supabase tables.

    The repository adapts to the platform's existing schema instead of creating
    duplicate Financial/Corporate tables. Evidence is aggregated across all
    compatible tables. Missing relationships remain missing rather than becoming
    synthetic risk.
    """

    DEFAULT_TABLES = {
        "supply_chain": [
            "sc_company_exposure",
            "corporate_exposures",
            "supply_chain_company_exposures",
            "supply_chain_exposures",
            "supply_chain_risk_scores",
        ],
        "country": ["corporate_exposures", "corporate_country_exposures", "country_corporate_exposures"],
        "conflict": ["corporate_exposures", "corporate_conflict_exposures", "conflict_corporate_exposures"],
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

    MODULE_ALIASES = {
        "supply_chain": {
            "supply_chain", "supply-chain", "supply chain", "logistics", "supplier",
            "semiconductor", "manufacturing", "critical_minerals", "critical minerals",
            "shipping", "chokepoint", "route_disruption", "route disruption",
        },
        "country": {"country", "country_risk", "country risk", "geopolitical", "geo", "political"},
        "conflict": {"conflict", "conflict_forecasting", "conflict forecasting", "war", "security"},
        "sanctions": {"sanctions", "sanction", "trade_controls", "export_control", "export controls"},
        "cyber": {"cyber", "cybersecurity", "information_ops", "information operations", "operational"},
    }

    COMPANY_REFERENCE_KEYS = (
        "company_entity_id", "target_entity_id", "corporate_entity_id", "ticker", "symbol",
        "company_ticker", "company_name", "company",
    )
    MODULE_DISCRIMINATOR_KEYS = (
        "module", "source_module", "domain", "risk_domain", "risk_type",
        "exposure_type", "category", "type",
    )

    COMPANY_LOOKUP_TABLES = ("companies", "corporate_companies", "company_profiles", "corporate_entities")
    COUNTRY_LOOKUP_TABLES = ("countries", "country_profiles", "country_intelligence_countries")

    CRITICALITY_SCORES = {
        "none": 0.0, "minimal": 10.0, "low": 25.0, "guarded": 35.0,
        "moderate": 50.0, "medium": 50.0, "elevated": 60.0,
        "high": 75.0, "severe": 85.0, "critical": 95.0,
    }

    def __init__(self, client=None) -> None:
        self.client = client
        self.entity_master = CorporateEntityMaster()
        self._company_fk_cache: Dict[str, Optional[str]] = {}
        self._country_fk_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        self._fk_diagnostics: Dict[str, List[Dict[str, Any]]] = {"company": [], "country": []}

    def _client(self):
        return self.client if self.client is not None else get_supabase_client()

    def candidate_tables(self, module: str) -> List[str]:
        override = (os.getenv(self.ENV_KEYS[module]) or "").strip()
        return [override] if override else list(self.DEFAULT_TABLES[module])

    def _fetch_table(self, table: str, limit: int) -> List[Dict[str, Any]]:
        response = self._client().table(table).select("*").limit(limit).execute()
        return [dict(row) for row in (getattr(response, "data", None) or []) if isinstance(row, Mapping)]

    def _fetch_by_id(self, table: str, value: str) -> Optional[Dict[str, Any]]:
        response = self._client().table(table).select("*").eq("id", value).limit(1).execute()
        rows = getattr(response, "data", None) or []
        return dict(rows[0]) if rows and isinstance(rows[0], Mapping) else None

    @staticmethod
    def _available_columns(rows: List[Mapping[str, Any]], cap: int = 80) -> List[str]:
        columns = set()
        for row in rows[:25]:
            columns.update(str(key) for key in row.keys())
        return sorted(columns)[:cap]

    @staticmethod
    def _sample_values(rows: List[Mapping[str, Any]], keys: List[str], cap: int = 10) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for key in keys:
            seen = set()
            values: List[str] = []
            for row in rows[:100]:
                raw = row.get(key)
                if raw is None:
                    continue
                value = str(raw).strip()
                if value and value not in seen:
                    seen.add(value)
                    values.append(value)
                if len(values) >= cap:
                    break
            if values:
                result[key] = values
        return result

    @staticmethod
    def _numeric_score(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if 0.0 <= number <= 1.0:
            number *= 100.0
        return max(0.0, min(100.0, number))

    @classmethod
    def _criticality_score(cls, value: Any) -> Optional[float]:
        numeric = cls._numeric_score(value)
        if numeric is not None:
            return numeric
        text = str(value or "").strip().lower()
        return cls.CRITICALITY_SCORES.get(text) if text else None

    def _resolve_reference(self, reference: str) -> Optional[str]:
        reference = str(reference or "").strip()
        if not reference:
            return None
        if reference.startswith("corp_"):
            return reference
        try:
            resolved = self.entity_master.resolve(reference)
        except Exception:
            resolved = None
        if isinstance(resolved, Mapping) and resolved.get("entity_id"):
            return str(resolved["entity_id"])
        return None

    def _resolve_company_fk(self, company_id: Any) -> Optional[str]:
        value = str(company_id or "").strip()
        if not value:
            return None
        if value in self._company_fk_cache:
            return self._company_fk_cache[value]
        for table in self.COMPANY_LOOKUP_TABLES:
            try:
                row = self._fetch_by_id(table, value)
            except Exception as exc:
                self._fk_diagnostics["company"].append({"table": table, "status": "unavailable", "detail": str(exc)[:180]})
                continue
            if not row:
                continue
            for key in ("entity_id", "ticker", "symbol", "name", "company_name", "legal_name"):
                resolved = self._resolve_reference(str(row.get(key) or ""))
                if resolved:
                    self._company_fk_cache[value] = resolved
                    self._fk_diagnostics["company"].append({"table": table, "status": "resolved", "id": value, "entity_id": resolved})
                    return resolved
        self._company_fk_cache[value] = None
        return None

    def _resolve_country_fk(self, country_id: Any) -> Optional[Dict[str, Any]]:
        value = str(country_id or "").strip()
        if not value:
            return None
        if value in self._country_fk_cache:
            return self._country_fk_cache[value]
        for table in self.COUNTRY_LOOKUP_TABLES:
            try:
                row = self._fetch_by_id(table, value)
            except Exception as exc:
                self._fk_diagnostics["country"].append({"table": table, "status": "unavailable", "detail": str(exc)[:180]})
                continue
            if row:
                normalized = {
                    "id": value,
                    "iso3": row.get("iso3") or row.get("country_iso3") or row.get("iso_code"),
                    "name": row.get("name") or row.get("country_name"),
                    "risk_score": row.get("risk_score") or row.get("overall_risk_score"),
                }
                self._country_fk_cache[value] = normalized
                self._fk_diagnostics["country"].append({"table": table, "status": "resolved", **normalized})
                return normalized
        self._country_fk_cache[value] = None
        return None

    def _resolve_company_entity_id(self, row: Mapping[str, Any]) -> Optional[str]:
        for key in self.COMPANY_REFERENCE_KEYS:
            resolved = self._resolve_reference(str(row.get(key) or ""))
            if resolved:
                return resolved
        return self._resolve_company_fk(row.get("company_id"))

    def _row_matches_module(self, module: str, row: Mapping[str, Any], table: str) -> bool:
        if table != "corporate_exposures":
            return True
        values = [str(row.get(key) or "").strip().lower() for key in self.MODULE_DISCRIMINATOR_KEYS]
        values = [value for value in values if value]
        aliases = self.MODULE_ALIASES[module]
        return any(value in aliases or any(alias in value for alias in aliases) for value in values)

    def _normalize_row(self, module: str, row: Mapping[str, Any], table: str) -> Optional[Dict[str, Any]]:
        if not self._row_matches_module(module, row, table):
            return None
        normalized = dict(row)
        company_entity_id = self._resolve_company_entity_id(normalized)
        if not company_entity_id:
            return None
        normalized["company_entity_id"] = company_entity_id

        if module == "supply_chain":
            dependency = (
                normalized.get("dependency_entity_id") or normalized.get("dependency_id") or normalized.get("supplier_id")
                or normalized.get("supplier_entity_id") or normalized.get("facility_id") or normalized.get("port_id")
                or normalized.get("chokepoint_id") or normalized.get("commodity_id") or normalized.get("source_entity_id")
            )
            if not dependency and normalized.get("commodity_code"):
                dependency = f"commodity:{normalized['commodity_code']}"
            if not dependency and normalized.get("commodity_name"):
                dependency = f"commodity:{str(normalized['commodity_name']).strip().lower().replace(' ', '_')}"
            if not dependency and normalized.get("supplier_country"):
                dependency = f"country:{normalized['supplier_country']}"
            if not dependency and normalized.get("country_id"):
                country = self._resolve_country_fk(normalized.get("country_id"))
                if country and country.get("iso3"):
                    dependency = f"country:{str(country['iso3']).upper()}"
                else:
                    dependency = f"country_id:{normalized['country_id']}"
            if dependency:
                normalized["dependency_entity_id"] = str(dependency)

            if table == "corporate_exposures":
                # exposure_level is already the table's aggregate strategic exposure score.
                # Use it as intensity once, not as both intensity and dependency share.
                exposure_level = self._numeric_score(normalized.get("exposure_level"))
                normalized.setdefault("dependency_share", 1.0)
                if exposure_level is not None:
                    normalized.setdefault("severity_score", exposure_level)
                    normalized.setdefault("severity_source", "stored_exposure_level")
                normalized.setdefault("relationship_type", str(normalized.get("exposure_type") or "strategic_supply_chain_exposure"))
                normalized.setdefault("confidence", 75.0)
            else:
                if normalized.get("dependency_share") is None:
                    normalized["dependency_share"] = normalized.get("dependency_pct") or normalized.get("exposure_share") or normalized.get("share") or normalized.get("weight")
                if normalized.get("severity_score") is None and normalized.get("risk_score") is None:
                    score = self._criticality_score(normalized.get("criticality"))
                    if score is not None:
                        normalized["severity_score"] = score
                        normalized["severity_source"] = "stored_criticality_category"
                normalized.setdefault("relationship_type", "commodity_dependency")
                normalized.setdefault("confidence", 75.0)

        elif module == "country":
            country = self._resolve_country_fk(normalized.get("country_id")) if normalized.get("country_id") else None
            if country:
                if country.get("iso3"):
                    normalized["country_iso3"] = str(country["iso3"]).upper()
                normalized["country_entity_id"] = str(country.get("id") or normalized.get("country_id"))
                if country.get("risk_score") is not None:
                    normalized.setdefault("country_risk_score", country.get("risk_score"))
            elif normalized.get("country_id"):
                normalized["country_entity_id"] = str(normalized["country_id"])
            normalized.setdefault("exposure_share", 1.0)
            exposure_level = self._numeric_score(normalized.get("exposure_level"))
            if exposure_level is not None:
                normalized.setdefault("severity_score", exposure_level)
            normalized.setdefault("confidence", 70.0)

        elif module == "conflict":
            normalized.setdefault("conflict_id", normalized.get("event_id") or normalized.get("scenario_id") or normalized.get("source_entity_id"))
        elif module == "sanctions":
            normalized.setdefault("counterparty_entity_id", normalized.get("sanctioned_entity_id") or normalized.get("counterparty_id") or normalized.get("source_entity_id"))
        elif module == "cyber":
            normalized.setdefault("incident_id", normalized.get("cyber_incident_id") or normalized.get("campaign_id") or normalized.get("event_id") or normalized.get("source_entity_id"))
        return normalized

    @staticmethod
    def _compatible(module: str, row: Mapping[str, Any]) -> bool:
        if not row.get("company_entity_id"):
            return False
        keys = {
            "supply_chain": ("dependency_entity_id", "supplier_entity_id", "facility_id", "port_id", "chokepoint_id", "commodity_id", "source_entity_id"),
            "country": ("country_iso3", "country_entity_id", "iso3", "country_code"),
            "conflict": ("conflict_id", "scenario_id", "event_id", "source_entity_id"),
            "sanctions": ("counterparty_entity_id", "sanctioned_entity_id", "counterparty_id", "source_entity_id"),
            "cyber": ("incident_id", "cyber_incident_id", "campaign_id", "actor_id", "event_id", "source_entity_id"),
        }
        return any(row.get(key) for key in keys[module])

    def collect_module(self, module: str, limit: int = 1000) -> Dict[str, Any]:
        diagnostics: List[Dict[str, Any]] = []
        all_rows: List[Dict[str, Any]] = []
        selected_tables: List[str] = []
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
                "table": table, "status": "ok", "row_count": len(rows),
                "module_match_count": module_match_count,
                "compatible_row_count": len(normalized_rows),
            }
            if rows:
                diagnostic["available_columns"] = self._available_columns(rows)
                samples = self._sample_values(rows, ["company_name", "company_id", "country_id", "exposure_type", "exposure_level", "criticality", "dependency_pct"])
                if samples:
                    diagnostic["sample_values"] = samples
            diagnostics.append(diagnostic)
            if normalized_rows:
                selected_tables.append(table)
                all_rows.extend(normalized_rows)
        return {"module": module, "table": selected_tables[0] if len(selected_tables) == 1 else None, "tables": selected_tables, "rows": all_rows, "diagnostics": diagnostics}

    def collect_all(self, limit_per_module: int = 1000) -> Dict[str, Any]:
        payloads: Dict[str, List[Dict[str, Any]]] = {}
        diagnostics: Dict[str, Any] = {}
        for module in self.DEFAULT_TABLES:
            result = self.collect_module(module, limit=limit_per_module)
            payloads[module] = result["rows"]
            diagnostics[module] = {
                "selected_table": result["table"],
                "selected_tables": result.get("tables", []),
                "attempts": result["diagnostics"],
            }
        diagnostics["foreign_key_resolution"] = self._fk_diagnostics
        return {
            "payloads": payloads,
            "diagnostics": diagnostics,
            "rule": "All compatible existing tables are aggregated. UUID foreign keys are resolved when a platform master table is available; absent relationships or severity are not inferred.",
        }
