from __future__ import annotations

import asyncio
import csv
import io
import re
import time
import urllib.request
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from services.supabase_client import get_supabase_client


class CrossModuleDynamicHazardService:
    """Resolve dynamic hazards for corporate exposure edges.

    Structural exposure and current hazard are intentionally separate. This
    service enriches existing exposure edges with current country/conflict
    conditions and adds company-specific sanctions/cyber evidence only when a
    positive, attributable match exists.
    """

    OFAC_SDN_CSV = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV"
    CACHE_TTL_SECONDS = 900

    def __init__(self, client=None) -> None:
        self.client = client
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _client(self):
        return self.client if self.client is not None else get_supabase_client()

    @staticmethod
    def _score(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if 0.0 <= number <= 1.0:
            number *= 100.0
        return round(max(0.0, min(100.0, number)), 2)

    @staticmethod
    def _exposure_fraction(value: Any) -> Optional[float]:
        score = CrossModuleDynamicHazardService._score(value)
        if score is None:
            return None
        return round(score / 100.0, 4)

    def _cache_get(self, key: str):
        item = self._cache.get(key)
        if not item:
            return None
        created_at, value = item
        if time.time() - created_at > self.CACHE_TTL_SECONDS:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value: Any) -> Any:
        self._cache[key] = (time.time(), value)
        return value

    @staticmethod
    def _normalize_name(value: str) -> str:
        text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
        suffixes = {
            "inc", "incorporated", "corp", "corporation", "co", "company",
            "ltd", "limited", "llc", "plc", "nv", "sa", "ag", "holdings", "holding",
        }
        tokens = [token for token in text.split() if token not in suffixes]
        return " ".join(tokens)

    @classmethod
    def _entity_aliases(cls, entity: Mapping[str, Any]) -> List[str]:
        values: List[str] = []
        for key in ("legal_name", "common_name"):
            value = str(entity.get(key) or "").strip()
            if value:
                values.append(value)
        values.extend(str(v).strip() for v in (entity.get("tickers") or []) if str(v).strip())
        normalized = []
        seen = set()
        for value in values:
            candidate = cls._normalize_name(value)
            if candidate and candidate not in seen:
                seen.add(candidate)
                normalized.append(candidate)
        return normalized

    def country_hazard(self, iso3: str) -> Dict[str, Any]:
        iso3 = str(iso3 or "").strip().upper()
        if not iso3:
            return {"status": "missing", "score": None, "reason": "missing_iso3"}
        cache_key = f"country:{iso3}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        attempts: List[Dict[str, Any]] = []
        try:
            response = (
                self._client().table("country_risk_scores")
                .select("*")
                .eq("iso3", iso3)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(response, "data", None) or []
            if rows:
                row = dict(rows[0])
                score = self._score(row.get("overall_score"))
                if score is not None:
                    return self._cache_set(cache_key, {
                        "status": "observed",
                        "score": score,
                        "confidence": 90.0,
                        "source": "Country Intelligence",
                        "source_table": "country_risk_scores",
                        "iso3": iso3,
                        "risk_level": row.get("risk_level"),
                        "updated_at": row.get("updated_at"),
                        "methodology": "country_intelligence_stored_deterministic_score",
                    })
            attempts.append({"table": "country_risk_scores", "status": "empty"})
        except Exception as exc:
            attempts.append({"table": "country_risk_scores", "status": "error", "detail": str(exc)[:220]})

        try:
            response = (
                self._client().table("country_intelligence_reports")
                .select("*")
                .eq("iso3", iso3)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(response, "data", None) or []
            if rows:
                row = dict(rows[0])
                score = self._score(row.get("risk_score"))
                if score is not None:
                    return self._cache_set(cache_key, {
                        "status": "observed",
                        "score": score,
                        "confidence": 82.0,
                        "source": "Country Intelligence",
                        "source_table": "country_intelligence_reports",
                        "iso3": iso3,
                        "risk_level": row.get("risk_level"),
                        "created_at": row.get("created_at"),
                        "methodology": "country_intelligence_latest_report_score",
                    })
            attempts.append({"table": "country_intelligence_reports", "status": "empty"})
        except Exception as exc:
            attempts.append({"table": "country_intelligence_reports", "status": "error", "detail": str(exc)[:220]})

        return self._cache_set(cache_key, {
            "status": "missing",
            "score": None,
            "iso3": iso3,
            "attempts": attempts,
            "reason": "no_stored_country_hazard",
        })

    def country_name(self, iso3: str) -> Optional[str]:
        iso3 = str(iso3 or "").strip().upper()
        if not iso3:
            return None
        cache_key = f"country-name:{iso3}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        for table in ("country_registry", "countries"):
            try:
                response = self._client().table(table).select("*").eq("iso3", iso3).limit(1).execute()
                rows = getattr(response, "data", None) or []
                if rows:
                    row = dict(rows[0])
                    name = row.get("country_name") or row.get("name")
                    if name:
                        return self._cache_set(cache_key, str(name))
            except Exception:
                continue
        return self._cache_set(cache_key, iso3)

    def conflict_hazard(self, iso3: str) -> Dict[str, Any]:
        iso3 = str(iso3 or "").strip().upper()
        if not iso3:
            return {"status": "missing", "score": None, "reason": "missing_iso3"}
        cache_key = f"conflict:{iso3}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        country = self.country_name(iso3) or iso3
        try:
            from app.services.conflict_data_sources import fetch_conflict_signals
            from app.services.conflict_scoring import calculate_conflict_score

            package = fetch_conflict_signals(country=country, indicator=None, limit=10)
            scoring = calculate_conflict_score(package.get("signals") or {})
            score = self._score(scoring.get("risk_score"))
            result = {
                "status": "observed" if score is not None else "missing",
                "score": score,
                "confidence": 70.0 if score is not None else None,
                "source": "Conflict Forecasting",
                "iso3": iso3,
                "country": country,
                "risk_level": scoring.get("risk_level"),
                "risk_drivers": scoring.get("risk_drivers", []),
                "source_mode": package.get("source_mode"),
                "live_item_count": len(package.get("rss_items") or []),
                "fetched_at": package.get("fetched_at"),
                "methodology": "existing_conflict_scoring_hybrid_signal_v1",
                "caveat": "Conflict score is an operational risk index, not a calibrated probability.",
            }
            return self._cache_set(cache_key, result)
        except Exception as exc:
            return self._cache_set(cache_key, {
                "status": "error",
                "score": None,
                "iso3": iso3,
                "country": country,
                "error": str(exc)[:240],
            })

    def _load_ofac_names(self) -> Dict[str, Any]:
        cache_key = "ofac:sdn:names"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        request = urllib.request.Request(
            self.OFAC_SDN_CSV,
            headers={"User-Agent": "SovereignIntelligenceAI/1.0 sanctions-screening"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = response.read().decode("utf-8-sig", errors="replace")
            reader = csv.reader(io.StringIO(payload))
            names: Dict[str, str] = {}
            for row in reader:
                if len(row) < 2:
                    continue
                raw_name = str(row[1] or "").strip()
                normalized = self._normalize_name(raw_name)
                if normalized:
                    names[normalized] = raw_name
            return self._cache_set(cache_key, {
                "status": "ok",
                "names": names,
                "record_count": len(names),
                "source_url": self.OFAC_SDN_CSV,
            })
        except Exception as exc:
            return self._cache_set(cache_key, {
                "status": "error",
                "names": {},
                "record_count": 0,
                "source_url": self.OFAC_SDN_CSV,
                "error": str(exc)[:240],
            })

    def sanctions_screen(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        dataset = self._load_ofac_names()
        aliases = self._entity_aliases(entity)
        if dataset.get("status") != "ok":
            return {
                "status": "error",
                "match": False,
                "score": None,
                "source": "OFAC Sanctions List Service",
                "error": dataset.get("error"),
                "source_url": dataset.get("source_url"),
            }
        names = dataset.get("names") or {}
        for alias in aliases:
            if alias in names:
                return {
                    "status": "positive_match",
                    "match": True,
                    "score": 100.0,
                    "confidence": 98.0,
                    "source": "OFAC Sanctions List Service",
                    "matched_name": names[alias],
                    "matched_alias": alias,
                    "source_url": dataset.get("source_url"),
                    "screening_method": "normalized_exact_name_match",
                    "caveat": "Direct name match requires compliance review; this is not legal advice.",
                }
        return {
            "status": "screened_no_direct_match",
            "match": False,
            "score": None,
            "source": "OFAC Sanctions List Service",
            "source_url": dataset.get("source_url"),
            "record_count": dataset.get("record_count"),
            "screening_method": "normalized_exact_name_match",
            "caveat": "No direct SDN name match does not establish zero sanctions or export-control risk.",
        }

    @staticmethod
    def _run_async(coro):
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def cyber_screen(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        aliases = self._entity_aliases(entity)
        company_key = str(entity.get("entity_id") or entity.get("common_name") or "company")
        cache_key = f"cyber:{company_key}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            from app.cyber_information.collectors.cisa_kev import CisaKevCollector

            result = self._run_async(CisaKevCollector().collect(limit=1000))
            records = result.get("records") or []
            matched: List[Dict[str, Any]] = []
            for record in records:
                vendor = self._normalize_name(str(record.get("vendor") or ""))
                if vendor and any(vendor == alias or vendor in alias or alias in vendor for alias in aliases if len(alias) >= 3):
                    matched.append(record)
            if not matched:
                return self._cache_set(cache_key, {
                    "status": "screened_no_company_match",
                    "score": None,
                    "source": "CISA Known Exploited Vulnerabilities",
                    "matched_count": 0,
                    "catalog_count": len(records),
                    "caveat": "No vendor match does not establish zero cyber or operational risk.",
                })
            ransomware = sum(
                1 for item in matched
                if str(item.get("known_ransomware_use") or "").strip().lower() in {"known", "yes", "true"}
            )
            score = min(100.0, 35.0 + min(len(matched), 6) * 8.0 + ransomware * 12.0)
            return self._cache_set(cache_key, {
                "status": "observed",
                "score": round(score, 2),
                "confidence": 94.0,
                "source": "CISA Known Exploited Vulnerabilities",
                "matched_count": len(matched),
                "ransomware_linked_count": ransomware,
                "matched_vulnerabilities": [
                    {
                        "cve": item.get("source_record_id"),
                        "vendor": item.get("vendor"),
                        "product": item.get("product"),
                        "date_added": item.get("date_added"),
                        "known_ransomware_use": item.get("known_ransomware_use"),
                        "provenance": item.get("provenance"),
                    }
                    for item in matched[:20]
                ],
                "methodology": "company_vendor_matched_cisa_kev_pressure_v1",
                "caveat": "Vendor-level KEV presence does not prove the company itself is compromised.",
            })
        except Exception as exc:
            return self._cache_set(cache_key, {
                "status": "error",
                "score": None,
                "source": "CISA Known Exploited Vulnerabilities",
                "error": str(exc)[:240],
            })

    def enrich(
        self,
        *,
        company_entity_id: str,
        entity: Mapping[str, Any],
        edges: Iterable[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        enriched: List[Dict[str, Any]] = [dict(edge) for edge in edges]
        country_hazards: Dict[str, Dict[str, Any]] = {}
        conflict_hazards: Dict[str, Dict[str, Any]] = {}
        added_edges: List[Dict[str, Any]] = []

        for edge in enriched:
            if str(edge.get("target_entity_id") or "") != company_entity_id:
                continue
            source = str(edge.get("source_entity_id") or "")
            if not source.startswith("country:"):
                continue
            iso3 = source.split(":", 1)[1].upper()
            evidence = dict(edge.get("evidence") or {})

            structural = self._exposure_fraction(evidence.get("exposure_level"))
            if structural is None:
                raw = evidence.get("structural_exposure")
                if raw is not None:
                    try:
                        structural = float(raw)
                        if structural > 1.0:
                            structural /= 100.0
                    except (TypeError, ValueError):
                        structural = None
            if structural is None:
                try:
                    structural = max(0.0, min(1.0, float(edge.get("weight") or 0.0)))
                except (TypeError, ValueError):
                    structural = 0.0
            structural = round(max(0.0, min(1.0, structural)), 4)
            evidence["structural_exposure"] = structural

            country = country_hazards.setdefault(iso3, self.country_hazard(iso3))
            conflict = conflict_hazards.setdefault(iso3, self.conflict_hazard(iso3))
            hazard_candidates = [
                value for value in (country.get("score"), conflict.get("score"))
                if self._score(value) is not None
            ]
            if hazard_candidates:
                hazard_score = max(float(v) for v in hazard_candidates)
                evidence["hazard_score"] = round(hazard_score, 2)
                evidence["hazard_source"] = "max(country_intelligence, conflict_forecasting)"
                evidence["hazard_components"] = {
                    "country": country,
                    "conflict": conflict,
                }
            if evidence.get("severity_source") == "stored_exposure_level":
                evidence["stored_exposure_intensity"] = evidence.get("severity_score")
                evidence.pop("severity_score", None)
            edge["weight"] = structural
            edge["evidence"] = evidence

            if country.get("score") is not None:
                added_edges.append({
                    "source_entity_id": f"country:{iso3}",
                    "target_entity_id": company_entity_id,
                    "relationship_type": "dynamic_country_hazard_exposure",
                    "weight": structural,
                    "source_module": "Country Intelligence",
                    "confidence": country.get("confidence", 85.0),
                    "evidence": {
                        "structural_exposure": structural,
                        "hazard_score": country.get("score"),
                        "hazard_source": country.get("source_table") or "country_intelligence",
                        "country_hazard": country,
                    },
                    "observed_at": country.get("updated_at") or country.get("created_at"),
                })
            if conflict.get("score") is not None:
                added_edges.append({
                    "source_entity_id": f"conflict:{iso3}",
                    "target_entity_id": company_entity_id,
                    "relationship_type": "dynamic_conflict_hazard_exposure",
                    "weight": structural,
                    "source_module": "Conflict Forecasting",
                    "confidence": conflict.get("confidence", 70.0),
                    "evidence": {
                        "structural_exposure": structural,
                        "hazard_score": conflict.get("score"),
                        "hazard_source": conflict.get("source_mode") or "conflict_forecasting",
                        "conflict_hazard": conflict,
                    },
                    "observed_at": conflict.get("fetched_at"),
                })

        sanctions = self.sanctions_screen(entity)
        if sanctions.get("match") and sanctions.get("score") is not None:
            added_edges.append({
                "source_entity_id": "ofac:direct_match",
                "target_entity_id": company_entity_id,
                "relationship_type": "direct_sanctions_designation_match",
                "weight": 1.0,
                "source_module": "Sanctions / Trade Intelligence",
                "confidence": sanctions.get("confidence", 98.0),
                "evidence": {
                    "structural_exposure": 1.0,
                    "hazard_score": sanctions.get("score"),
                    "hazard_source": "OFAC Sanctions List Service",
                    "screening": sanctions,
                },
                "observed_at": None,
            })

        cyber = self.cyber_screen(entity)
        if cyber.get("score") is not None:
            added_edges.append({
                "source_entity_id": "cyber:cisa_kev_vendor_pressure",
                "target_entity_id": company_entity_id,
                "relationship_type": "company_vendor_known_exploited_vulnerability_pressure",
                "weight": 1.0,
                "source_module": "Cyber & Information Operations",
                "confidence": cyber.get("confidence", 94.0),
                "evidence": {
                    "structural_exposure": 1.0,
                    "hazard_score": cyber.get("score"),
                    "hazard_source": "CISA Known Exploited Vulnerabilities",
                    "cyber_screening": cyber,
                },
                "observed_at": None,
            })

        enriched.extend(added_edges)
        return {
            "edges": enriched,
            "added_edge_count": len(added_edges),
            "country_hazards": country_hazards,
            "conflict_hazards": conflict_hazards,
            "sanctions_screening": sanctions,
            "cyber_screening": cyber,
            "methodology": "cross_module_dynamic_hazard_enrichment_v1",
            "rule": "Structural exposure is separated from dynamic hazard; absent evidence remains missing.",
        }
