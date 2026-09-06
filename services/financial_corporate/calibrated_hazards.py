from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .advanced_hazards import AdvancedCorporateHazardService


class CalibratedCorporateHazardService(AdvancedCorporateHazardService):
    """Calibrated signal-quality layer for corporate operational hazards.

    This preserves the validated dynamic-hazard graph and only tightens the noisy
    public-signal collectors. In particular:
    - NVD pressure is based on recently *published* CVEs, not recently modified
      legacy records;
    - media evidence is freshness- and source-quality-weighted;
    - cyber media distinguishes direct company incidents/product vulnerabilities
      from indirect ecosystem mentions;
    - trade-control reporting is treated as policy pressure, not a legal finding.
    """

    NVD_LOOKBACK_DAYS = 120

    HIGH_QUALITY_SOURCES = {
        "reuters",
        "associated press",
        "ap news",
        "bloomberg",
        "financial times",
        "the wall street journal",
        "wall street journal",
        "cnbc",
        "bbc",
        "cnn",
        "the register",
        "bleepingcomputer",
        "securityweek",
        "techcrunch",
        "csis | center for strategic and international studies",
        "center for strategic and international studies",
    }

    MEDIUM_QUALITY_SOURCES = {
        "yahoo finance",
        "south china morning post",
        "scworld.com",
        "dark reading",
        "therecord.media",
        "the record",
        "tech times",
    }

    @staticmethod
    def _published_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = parsedate_to_datetime(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            pass
        return CalibratedCorporateHazardService._parse_datetime(text)

    @classmethod
    def _media_freshness(cls, value: Any) -> float:
        dt = cls._published_datetime(value)
        if dt is None:
            return 0.5
        age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
        if age_days <= 7:
            return 1.0
        if age_days <= 30:
            return 0.9
        if age_days <= 90:
            return 0.75
        if age_days <= 180:
            return 0.55
        return 0.35

    @classmethod
    def _source_weight(cls, source: Any) -> float:
        normalized = str(source or "").strip().lower()
        if normalized in cls.HIGH_QUALITY_SOURCES:
            return 1.0
        if normalized in cls.MEDIUM_QUALITY_SOURCES:
            return 0.8
        return 0.6

    @staticmethod
    def _company_tokens(entity: Mapping[str, Any]) -> List[str]:
        values = [entity.get("common_name"), entity.get("legal_name")]
        tokens: List[str] = []
        for value in values:
            text = str(value or "").strip().lower()
            if not text:
                continue
            tokens.append(text)
            if " corporation" in text:
                tokens.append(text.replace(" corporation", "").strip())
            if " inc." in text:
                tokens.append(text.replace(" inc.", "").strip())
            if " inc" in text:
                tokens.append(text.replace(" inc", "").strip())
        return sorted(set(token for token in tokens if token), key=len, reverse=True)

    @classmethod
    def _direct_cyber_relevance(cls, entity: Mapping[str, Any], title: Any) -> float:
        text = str(title or "").strip().lower()
        names = cls._company_tokens(entity)
        if not text or not any(name in text for name in names):
            return 0.0

        direct_phrases = [
            " confirms ",
            " confirmed ",
            " patches ",
            " patch ",
            " vulnerability",
            " vulnerabilities",
            " security flaw",
            " cve-",
            " exploit",
            " zero-day",
            " zero day",
            " data breach",
            " breached",
            " ransomware",
            " cyberattack",
        ]
        product_terms = ["gpu", "driver", "geforce", "cuda", "nemo", "firmware", "software", "server"]

        for name in names:
            idx = text.find(name)
            if idx < 0:
                continue
            window = text[max(0, idx - 45): min(len(text), idx + len(name) + 70)]
            if any(term in window for term in direct_phrases):
                return 1.0
            if any(term in text for term in product_terms) and any(
                term in text for term in ["vulnerability", "flaw", "cve", "exploit", "patch"]
            ):
                return 0.9

        # The company is mentioned, but the incident may belong to a supplier,
        # customer, partner, or another company. Preserve it as ecosystem context
        # without treating it as a direct enterprise incident.
        return 0.3

    @staticmethod
    def _severity_from_title(title: Any, *, cyber: bool) -> Optional[str]:
        text = str(title or "").lower()
        if cyber:
            severe_terms = ["ransomware", "data breach", "breached", "cyberattack", "actively exploited", "zero-day", "zero day"]
            moderate_terms = ["vulnerability", "vulnerabilities", "security flaw", "cve", "patch", "exploit"]
        else:
            severe_terms = ["export ban", "blacklist", "entity list", "license restriction", "sanctioned", "blocked"]
            moderate_terms = ["export control", "export restriction", "trade restriction", "license requirement", "china chip", "commerce department", "bis"]
        if any(term in text for term in severe_terms):
            return "high"
        if any(term in text for term in moderate_terms):
            return "moderate"
        return None

    def _weighted_media_pressure(
        self,
        *,
        entity: Mapping[str, Any],
        items: List[Mapping[str, Any]],
        cyber: bool,
    ) -> Dict[str, Any]:
        matched: List[Dict[str, Any]] = []
        weighted_points = 0.0
        direct_count = 0
        ecosystem_count = 0
        high_count = 0
        moderate_count = 0

        company_names = self._company_tokens(entity)
        for item in items:
            title = str(item.get("title") or "")
            lower_title = title.lower()
            if not any(name in lower_title for name in company_names):
                continue
            severity = self._severity_from_title(title, cyber=cyber)
            if severity is None:
                continue

            freshness = self._media_freshness(item.get("published"))
            source_weight = self._source_weight(item.get("source"))
            relevance = self._direct_cyber_relevance(entity, title) if cyber else 1.0
            if relevance <= 0:
                continue

            base_points = 16.0 if severity == "high" else 8.0
            contribution = base_points * freshness * source_weight * relevance
            weighted_points += contribution
            if severity == "high":
                high_count += 1
            else:
                moderate_count += 1
            if relevance >= 0.8:
                direct_count += 1
                relevance_label = "direct"
            else:
                ecosystem_count += 1
                relevance_label = "ecosystem"

            matched.append({
                **dict(item),
                "signal_severity": severity,
                "relevance": relevance_label,
                "freshness_weight": round(freshness, 2),
                "source_quality_weight": round(source_weight, 2),
                "weighted_points": round(contribution, 2),
            })

        if not matched:
            return {
                "score": None,
                "confidence": None,
                "high_count": 0,
                "moderate_count": 0,
                "direct_count": 0,
                "ecosystem_count": 0,
                "matched": [],
            }

        # A small base plus accumulated evidence. The cap deliberately prevents
        # headline volume alone from creating a near-critical company hazard.
        score = min(82.0, 10.0 + weighted_points)
        avg_source = sum(float(item["source_quality_weight"]) for item in matched) / len(matched)
        direct_share = direct_count / len(matched)
        confidence = min(90.0, 50.0 + min(len(matched), 8) * 3.0 + avg_source * 10.0 + direct_share * 8.0)
        return {
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "high_count": high_count,
            "moderate_count": moderate_count,
            "direct_count": direct_count,
            "ecosystem_count": ecosystem_count,
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

        pressure = self._weighted_media_pressure(entity=entity, items=news.get("items") or [], cyber=False)
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
            "severe_signal_count": pressure["high_count"],
            "moderate_signal_count": pressure["moderate_count"],
            "matched_items": pressure["matched"],
            "methodology": "company_trade_control_media_pressure_v2_quality_freshness_weighted",
            "caveat": "Operational policy-pressure index; not a legal sanctions determination.",
        }

    def nvd_company_pressure(self, entity: Mapping[str, Any]) -> Dict[str, Any]:
        name = self._entity_query_name(entity)
        if not name:
            return {"status": "missing", "score": None, "reason": "missing_company_name"}
        key = f"nvd-published:{name.lower()}:{self.NVD_LOOKBACK_DAYS}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self.NVD_LOOKBACK_DAYS)
        params = {
            "keywordSearch": name,
            "pubStartDate": start.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "pubEndDate": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "resultsPerPage": 50,
        }
        url = f"{self.NVD_URL}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))

            matches: List[Dict[str, Any]] = []
            cvss_values: List[float] = []
            for wrapper in payload.get("vulnerabilities") or []:
                cve = wrapper.get("cve") or {}
                published = self._parse_datetime(cve.get("published"))
                if published is None or published < start or published > end:
                    continue
                descriptions = cve.get("descriptions") or []
                english = next((d.get("value") for d in descriptions if d.get("lang") == "en"), "") or ""
                if name.lower() not in english.lower():
                    continue
                cvss = self._cvss_score(cve)
                if cvss is not None:
                    cvss_values.append(cvss)
                matches.append({
                    "cve": cve.get("id"),
                    "published": cve.get("published"),
                    "last_modified": cve.get("lastModified"),
                    "cvss_base_score": cvss,
                    "description": english[:500],
                })

            if not matches:
                return self._cache_set(key, {
                    "status": "screened_no_recent_published_match",
                    "score": None,
                    "source": "NIST National Vulnerability Database",
                    "source_url": self.NVD_URL,
                    "lookback_days": self.NVD_LOOKBACK_DAYS,
                    "date_basis": "published",
                    "caveat": "No recently published NVD keyword match does not establish zero cyber risk.",
                })

            max_cvss = max(cvss_values) if cvss_values else 0.0
            avg_cvss = sum(cvss_values) / len(cvss_values) if cvss_values else 0.0
            score = min(85.0, max(15.0, max_cvss * 5.5 + avg_cvss * 1.5 + min(len(matches), 6) * 2.0))
            confidence = min(90.0, 66.0 + min(len(matches), 8) * 3.0)
            return self._cache_set(key, {
                "status": "observed",
                "score": round(score, 2),
                "confidence": round(confidence, 2),
                "source": "NIST National Vulnerability Database",
                "source_url": self.NVD_URL,
                "lookback_days": self.NVD_LOOKBACK_DAYS,
                "date_basis": "published",
                "matched_count": len(matches),
                "max_cvss_base_score": round(max_cvss, 1),
                "average_cvss_base_score": round(avg_cvss, 2),
                "matched_vulnerabilities": matches[:15],
                "methodology": "company_keyword_recent_published_nvd_pressure_v2",
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

        pressure = self._weighted_media_pressure(entity=entity, items=news.get("items") or [], cyber=True)
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
            "severe_signal_count": pressure["high_count"],
            "moderate_signal_count": pressure["moderate_count"],
            "direct_signal_count": pressure["direct_count"],
            "ecosystem_signal_count": pressure["ecosystem_count"],
            "matched_items": pressure["matched"],
            "methodology": "company_cyber_media_pressure_v2_directness_quality_freshness_weighted",
            "caveat": "Operational cyber-pressure index; indirect ecosystem events are down-weighted and reports require source-level verification.",
        }

    def enrich(self, *, company_entity_id: str, entity: Mapping[str, Any], edges: List[Mapping[str, Any]]) -> Dict[str, Any]:
        result = super().enrich(company_entity_id=company_entity_id, entity=entity, edges=edges)
        result["methodology"] = "cross_module_dynamic_hazard_enrichment_v3_calibrated_signal_quality"
        result["calibration_rules"] = [
            "NVD current pressure uses CVE publication date rather than modification date.",
            "Media signals are weighted by source quality and evidence freshness.",
            "Indirect cyber ecosystem mentions are down-weighted relative to direct company incidents.",
            "Media volume alone cannot create a near-critical operational hazard.",
        ]
        return result
