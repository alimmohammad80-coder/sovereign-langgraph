from __future__ import annotations

import json
import math
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .cross_module_hazards import CrossModuleDynamicHazardService


class AdvancedCorporateHazardService:
    """Production hardening layer for corporate dynamic hazards.

    This wrapper preserves the validated cross-module hazard service while adding:
    - evidence freshness decay for stored country assessments;
    - company-specific trade-control policy pressure from current public reporting;
    - NVD company/product vulnerability pressure to complement CISA KEV;
    - entity-scoped output so one company response never leaks unrelated edges.

    Scores are deterministic operational indices, not probabilities or legal advice.
    Missing evidence remains missing.
    """

    CACHE_TTL_SECONDS = 900
    USER_AGENT = "SovereignIntelligenceAI/1.0 corporate-risk-research"
    NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

    def __init__(self, base: Optional[CrossModuleDynamicHazardService] = None) -> None:
        self.base = base or CrossModuleDynamicHazardService()
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _cache_get(self, key: str):
        item = self._cache.get(key)
        if not item:
            return None
        created_at, value = item
        if time.time() - created_at > self.CACHE_TTL_SECONDS:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value: Any):
        self._cache[key] = (time.time(), value)
        return value

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    @classmethod
    def freshness(cls, observed_at: Any, base_confidence: Any) -> Dict[str, Any]:
        try:
            base = max(0.0, min(100.0, float(base_confidence)))
        except (TypeError, ValueError):
            base = 0.0
        dt = cls._parse_datetime(observed_at)
        if dt is None:
            return {
                "age_days": None,
                "freshness_factor": 0.6,
                "freshness_status": "unknown_age",
                "base_confidence": base,
                "effective_confidence": round(base * 0.6, 2),
            }
        age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
        if age_days <= 7:
            factor, status = 1.0, "fresh"
        elif age_days <= 30:
            factor, status = 0.9, "recent"
        elif age_days <= 60:
            factor, status = 0.75, "aging"
        elif age_days <= 90:
            factor, status = 0.6, "stale"
        else:
            # Slow exponential tail with a floor: old evidence can provide context,
            # but should never retain full evidentiary confidence indefinitely.
            factor = max(0.25, 0.6 * math.exp(-(age_days - 90.0) / 120.0))
            status = "stale"
        return {
            "age_days": round(age_days, 2),
            "freshness_factor": round(factor, 4),
            "freshness_status": status,
            "base_confidence": round(base, 2),
            "effective_confidence": round(base * factor, 2),
        }

    @staticmethod
    def _entity_query_name(entity: Mapping[str, Any]) -> str:
        return str(entity.get("common_name") or entity.get("legal_name") or "").strip()

    def _fetch_google_news(self, query: str, *, limit: int = 15) -> Dict[str, Any]:
        key = f"news:{query.lower()}:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        params = urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        url = f"{self.GOOGLE_NEWS_RSS}?{params}"
        request = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = response.read()
            root = ET.fromstring(payload)
            items: List[Dict[str, Any]] = []
            for item in root.findall("./channel/item")[:limit]:
                items.append({
                    "title": item.findtext("title"),
                    "link": item.findtext("link"),
                    "published": item.findtext("pubDate"),
                    "source": item.findtext("source"),
                })
            return self._cache_set(key, {"status": "ok", "count": len(items), "items": items, "source_url": url})
        except Exception as exc:
            return self._cache_set(key, {"status": "error", "count": 0, "items": [], "source_url": url, "error": str(exc)[:240]})

    @staticmethod
    def _keyword_pressure(items: List[Mapping[str, Any]], severe_terms: List[str], moderate_terms: List[str]) -> Dict[str, Any]:
        severe = 0
        moderate = 0
        matched: List[Dict[str, Any]] = []
        for item in items:
            title = str(item.get("title") or "").lower()
            severity = None
            if any(term in title for term in severe_terms):
                severe += 1
                severity = "high"
            elif any(term in title for term in moderate_terms):
                moderate += 1
                severity = "moderate"
            if severity:
                matched.append({**dict(item), "signal_severity": severity})
        if not matched:
            return {"score": None, "confidence": None, "severe_count": 0, "moderate_count": 0, "matched": []}
        score = min(85.0, 18.0 + severe * 14.0 + moderate * 7.0)
        confidence = min(86.0, 55.0 + len(matched) * 4.0)
        return {
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "severe_count": severe,
            "moderate_count": moderate,
            "matched": matched[:10],
        }

    def trade_control_pressure(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        name = self._entity_query_name(entity)
        if not name:
            return {"status": "missing", "score": None, "reason": "missing_company_name"}
        query = f'"{name}" ("export controls" OR "export restrictions" OR sanctions OR "trade restrictions" OR BIS)'
        news = self._fetch_google_news(query, limit=20)
        if news.get("status") != "ok":
            return {"status": "error", "score": None, "source": "Google News RSS", "error": news.get("error")}
        pressure = self._keyword_pressure(
            news.get("items") or [],
            severe_terms=["export ban", "blacklist", "entity list", "license restriction", "sanctioned", "blocked"],
            moderate_terms=["export control", "export restriction", "trade restriction", "license requirement", "china chip", "commerce department", "bis"],
        )
        if pressure.get("score") is None:
            return {
                "status": "screened_no_material_signal",
                "score": None,
                "source": "Google News RSS",
                "query": query,
                "item_count": news.get("count"),
                "caveat": "No current media signal does not establish zero sanctions or trade-control exposure.",
            }
        return {
            "status": "observed",
            "score": pressure["score"],
            "confidence": pressure["confidence"],
            "source": "Google News RSS",
            "query": query,
            "item_count": news.get("count"),
            "severe_signal_count": pressure["severe_count"],
            "moderate_signal_count": pressure["moderate_count"],
            "matched_items": pressure["matched"],
            "methodology": "company_trade_control_media_pressure_v1",
            "caveat": "Operational policy-pressure index; not a legal sanctions determination.",
        }

    @staticmethod
    def _cvss_score(cve: Mapping[str, Any]) -> Optional[float]:
        metrics = cve.get("metrics") or {}
        for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            values = metrics.get(key) or []
            for metric in values:
                data = metric.get("cvssData") or {}
                value = data.get("baseScore")
                try:
                    if value is not None:
                        return float(value)
                except (TypeError, ValueError):
                    pass
        return None

    def nvd_company_pressure(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        name = self._entity_query_name(entity)
        if not name:
            return {"status": "missing", "score": None, "reason": "missing_company_name"}
        key = f"nvd:{name.lower()}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=120)
        params = {
            "keywordSearch": name,
            "lastModStartDate": start.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "lastModEndDate": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "resultsPerPage": 50,
        }
        url = f"{self.NVD_URL}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            matches: List[Dict[str, Any]] = []
            max_cvss = 0.0
            for wrapper in payload.get("vulnerabilities") or []:
                cve = wrapper.get("cve") or {}
                descriptions = cve.get("descriptions") or []
                english = next((d.get("value") for d in descriptions if d.get("lang") == "en"), "") or ""
                if name.lower() not in english.lower():
                    continue
                cvss = self._cvss_score(cve)
                if cvss is not None:
                    max_cvss = max(max_cvss, cvss)
                matches.append({
                    "cve": cve.get("id"),
                    "published": cve.get("published"),
                    "last_modified": cve.get("lastModified"),
                    "cvss_base_score": cvss,
                    "description": english[:500],
                })
            if not matches:
                return self._cache_set(key, {
                    "status": "screened_no_recent_match",
                    "score": None,
                    "source": "NIST National Vulnerability Database",
                    "source_url": self.NVD_URL,
                    "lookback_days": 120,
                    "caveat": "No recent NVD keyword match does not establish zero cyber risk.",
                })
            score = min(90.0, max(20.0, max_cvss * 8.0 + min(len(matches), 8) * 2.0))
            confidence = min(92.0, 72.0 + min(len(matches), 10) * 2.0)
            return self._cache_set(key, {
                "status": "observed",
                "score": round(score, 2),
                "confidence": round(confidence, 2),
                "source": "NIST National Vulnerability Database",
                "source_url": self.NVD_URL,
                "lookback_days": 120,
                "matched_count": len(matches),
                "max_cvss_base_score": round(max_cvss, 1),
                "matched_vulnerabilities": matches[:15],
                "methodology": "company_keyword_recent_nvd_pressure_v1",
                "caveat": "Product vulnerability pressure does not prove compromise of the company enterprise.",
            })
        except Exception as exc:
            return self._cache_set(key, {
                "status": "error",
                "score": None,
                "source": "NIST National Vulnerability Database",
                "source_url": self.NVD_URL,
                "error": str(exc)[:240],
            })

    def cyber_media_pressure(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        name = self._entity_query_name(entity)
        if not name:
            return {"status": "missing", "score": None, "reason": "missing_company_name"}
        query = f'"{name}" (cyberattack OR breach OR ransomware OR vulnerability OR CVE OR "security flaw")'
        news = self._fetch_google_news(query, limit=20)
        if news.get("status") != "ok":
            return {"status": "error", "score": None, "source": "Google News RSS", "error": news.get("error")}
        pressure = self._keyword_pressure(
            news.get("items") or [],
            severe_terms=["ransomware", "data breach", "cyberattack", "actively exploited", "zero day", "zero-day"],
            moderate_terms=["vulnerability", "security flaw", "cve", "patch", "exploit"],
        )
        if pressure.get("score") is None:
            return {
                "status": "screened_no_material_signal",
                "score": None,
                "source": "Google News RSS",
                "query": query,
                "caveat": "No current media signal does not establish zero cyber risk.",
            }
        return {
            "status": "observed",
            "score": pressure["score"],
            "confidence": pressure["confidence"],
            "source": "Google News RSS",
            "query": query,
            "severe_signal_count": pressure["severe_count"],
            "moderate_signal_count": pressure["moderate_count"],
            "matched_items": pressure["matched"],
            "methodology": "company_cyber_media_pressure_v1",
            "caveat": "Operational cyber-pressure index; reports require source-level analyst verification.",
        }

    @staticmethod
    def _combined_signal(signals: List[Mapping[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
        observed = [s for s in signals if s.get("score") is not None]
        if not observed:
            return None, None
        contributions: List[float] = []
        confidences: List[float] = []
        for signal in observed:
            try:
                score = max(0.0, min(100.0, float(signal.get("score"))))
                confidence = max(0.0, min(100.0, float(signal.get("confidence") or 60.0)))
            except (TypeError, ValueError):
                continue
            contributions.append(score * confidence / 100.0)
            confidences.append(confidence)
        if not contributions:
            return None, None
        combined = 100.0 * (1.0 - math.prod(1.0 - c / 100.0 for c in contributions))
        return round(min(100.0, combined), 2), round(sum(confidences) / len(confidences), 2)

    def enrich(self, *, company_entity_id: str, entity: Mapping[str, Any], edges: List[Mapping[str, Any]]) -> Dict[str, Any]:
        base_result = self.base.enrich(company_entity_id=company_entity_id, entity=entity, edges=edges)

        # Strictly scope all returned graph edges to the requested company.
        scoped_edges: List[Dict[str, Any]] = [
            dict(edge) for edge in (base_result.get("edges") or [])
            if str(edge.get("target_entity_id") or "") == company_entity_id
        ]

        # Apply freshness decay to stored Country Intelligence confidence and
        # propagate it to the corresponding country hazard edges.
        country_hazards = dict(base_result.get("country_hazards") or {})
        for iso3, hazard in country_hazards.items():
            hazard = dict(hazard)
            observed_at = hazard.get("updated_at") or hazard.get("created_at")
            freshness = self.freshness(observed_at, hazard.get("confidence"))
            hazard["freshness"] = freshness
            hazard["raw_confidence"] = hazard.get("confidence")
            hazard["confidence"] = freshness["effective_confidence"]
            country_hazards[iso3] = hazard
            for edge in scoped_edges:
                if edge.get("source_module") != "Country Intelligence":
                    continue
                if str(edge.get("source_entity_id") or "") != f"country:{iso3}":
                    continue
                edge["confidence"] = freshness["effective_confidence"]
                evidence = dict(edge.get("evidence") or {})
                if isinstance(evidence.get("country_hazard"), Mapping):
                    evidence["country_hazard"] = hazard
                evidence["freshness"] = freshness
                edge["evidence"] = evidence

        # Broaden Sanctions / Trade Intelligence beyond direct OFAC designation.
        ofac = dict(base_result.get("sanctions_screening") or {})
        trade = self.trade_control_pressure(entity)
        trade_score, trade_confidence = self._combined_signal([ofac, trade])
        if trade_score is not None:
            scoped_edges.append({
                "source_entity_id": "trade-control:company-policy-pressure",
                "target_entity_id": company_entity_id,
                "relationship_type": "company_trade_control_policy_pressure",
                "weight": 1.0,
                "source_module": "Sanctions / Trade Intelligence",
                "confidence": trade_confidence,
                "evidence": {
                    "structural_exposure": 1.0,
                    "hazard_score": trade_score,
                    "hazard_source": "combined_ofac_and_company_trade_control_signals",
                    "ofac_screening": ofac,
                    "trade_control_pressure": trade,
                },
                "observed_at": datetime.now(timezone.utc).isoformat(),
            })

        # Broaden Cyber / Operational Intelligence with NVD and current reporting,
        # while retaining the original CISA KEV screening as a separate source.
        cisa = dict(base_result.get("cyber_screening") or {})
        nvd = self.nvd_company_pressure(entity)
        cyber_news = self.cyber_media_pressure(entity)
        cyber_score, cyber_confidence = self._combined_signal([cisa, nvd, cyber_news])
        if cyber_score is not None:
            scoped_edges.append({
                "source_entity_id": "cyber:company-operational-pressure",
                "target_entity_id": company_entity_id,
                "relationship_type": "company_cyber_operational_pressure",
                "weight": 1.0,
                "source_module": "Cyber & Information Operations",
                "confidence": cyber_confidence,
                "evidence": {
                    "structural_exposure": 1.0,
                    "hazard_score": cyber_score,
                    "hazard_source": "combined_cisa_nvd_company_cyber_signals",
                    "cisa_kev": cisa,
                    "nvd": nvd,
                    "cyber_media": cyber_news,
                },
                "observed_at": datetime.now(timezone.utc).isoformat(),
            })

        return {
            **base_result,
            "edges": scoped_edges,
            "company_entity_id": company_entity_id,
            "edge_scope": "requested_company_only",
            "country_hazards": country_hazards,
            "trade_control_pressure": trade,
            "cyber_nvd_pressure": nvd,
            "cyber_media_pressure": cyber_news,
            "advanced_added_edge_count": int(trade_score is not None) + int(cyber_score is not None),
            "methodology": "cross_module_dynamic_hazard_enrichment_v2_production_hardened",
            "rules": [
                "Structural exposure remains separate from dynamic hazard.",
                "Stored country evidence confidence decays with age.",
                "Negative screening does not imply zero risk.",
                "Returned graph edges are scoped to the requested company.",
            ],
        }
