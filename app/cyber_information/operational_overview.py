from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .collectors import CisaKevCollector, GdeltCollector, NvdCollector
from .collectors.base import CollectorError
from .cyber_engine import CyberIntelligenceEngine
from .information_engine import analyze_information_environment


engine = CyberIntelligenceEngine()


def _source_status(result: Any, source: str) -> dict[str, Any]:
    if isinstance(result, Exception):
        return {"source": source, "ok": False, "error": str(result)}
    return {"source": source, "ok": True, "count": int(result.get("count") or 0)}


def _priority_incidents(records: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    incidents = [engine.incident_from_record(record) for record in records]
    incidents.sort(key=lambda item: (item.severity_score, item.confidence.score), reverse=True)
    return [item.model_dump(mode="json") for item in incidents[:limit]]


def _priority_exposures(records: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    exposures = []
    for record in records:
        try:
            exposures.append(engine.vulnerability_exposure(record, target_criticality_score=70.0))
        except ValueError:
            continue
    exposures.sort(key=lambda item: (item.exposure_score, item.confidence.score), reverse=True)
    return [item.model_dump(mode="json") for item in exposures[:limit]]


def _vendor_pressure(kev_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(item.get("vendor") or "Unknown") for item in kev_records)
    return [{"vendor": vendor, "known_exploited_count": count} for vendor, count in counts.most_common(8)]


def _sector_relevance(text: str) -> list[str]:
    lowered = text.lower()
    mapping = {
        "energy": ("energy", "oil", "gas", "power", "electric", "utility"),
        "telecommunications": ("telecom", "telecommunications", "mobile", "carrier", "network operator"),
        "finance": ("bank", "financial", "finance", "payment", "exchange"),
        "government": ("government", "ministry", "agency", "public sector", "state network"),
        "transportation": ("port", "shipping", "rail", "aviation", "airport", "transport"),
        "defense": ("defense", "military", "armed forces", "aerospace"),
        "healthcare": ("hospital", "healthcare", "health system", "medical"),
        "technology": ("software", "cloud", "technology", "semiconductor", "chip"),
    }
    return [sector for sector, terms in mapping.items() if any(term in lowered for term in terms)]


def _information_products(records: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    analysis = analyze_information_environment(records, threshold=0.36)
    products = []
    for item in analysis.get("products", []):
        cluster = item.get("cluster", {})
        campaign = item.get("campaign", {})
        propagation = item.get("propagation", {})
        coordination = item.get("coordination", {})
        label = cluster.get("label") or campaign.get("name") or "Narrative cluster"
        text = f"{label} {cluster.get('representative_text') or ''}"
        products.append({
            "label": label,
            "observation_count": cluster.get("observation_count", 0),
            "velocity_score": cluster.get("velocity_score", 0),
            "reach_score": cluster.get("reach_score", 0),
            "strategic_relevance_score": cluster.get("strategic_relevance_score", 0),
            "propagation_score": propagation.get("propagation_score", 0),
            "coordination_score": coordination.get("coordination_score", 0),
            "coordination_level": coordination.get("coordination_level", "low"),
            "manipulation_likelihood_score": campaign.get("manipulation_likelihood_score", 0),
            "source_domains": cluster.get("source_domains", []),
            "countries": cluster.get("countries", []),
            "sectors": _sector_relevance(text),
            "confidence": campaign.get("confidence"),
            "caveats": coordination.get("caveats", []),
        })
    products.sort(
        key=lambda item: (
            item.get("strategic_relevance_score", 0),
            item.get("coordination_score", 0),
            item.get("propagation_score", 0),
        ),
        reverse=True,
    )
    return products[:limit]


def _executive_judgment(
    kev_records: list[dict[str, Any]],
    nvd_records: list[dict[str, Any]],
    narratives: list[dict[str, Any]],
) -> dict[str, Any]:
    ransomware = sum(
        1
        for item in kev_records
        if str(item.get("known_ransomware_use") or "").lower() in {"known", "yes", "true"}
    )
    top_narrative = narratives[0] if narratives else None
    pressure = min(100, 38 + min(len(kev_records), 40) + ransomware * 4 + min(len(nvd_records), 40) // 2)
    level = "Critical" if pressure >= 85 else "High" if pressure >= 70 else "Elevated" if pressure >= 55 else "Guarded"
    drivers = []
    if kev_records:
        drivers.append(f"{len(kev_records)} CISA-known exploited vulnerabilities are in the current collection window.")
    if ransomware:
        drivers.append(f"{ransomware} known exploited vulnerabilities are associated with ransomware campaign use.")
    if top_narrative:
        drivers.append(
            f"The highest-priority information cluster is '{top_narrative['label']}' with strategic relevance "
            f"{top_narrative['strategic_relevance_score']:.0f}/100 and coordination indicators "
            f"{top_narrative['coordination_score']:.0f}/100."
        )
    if not drivers:
        drivers.append("Current live-source coverage is insufficient for a material operational judgment.")
    return {
        "posture_score": pressure,
        "posture_level": level,
        "bluf": (
            f"Cyber and information operations posture is assessed as {level}. "
            "Prioritize confirmed exploitation, ransomware-linked vulnerabilities, and high-relevance narrative clusters; "
            "coordination indicators are analytic signals and do not by themselves establish orchestration or attribution."
        ),
        "key_drivers": drivers,
    }


async def build_operational_overview(
    *,
    kev_limit: int = 80,
    nvd_limit: int = 80,
    gdelt_limit: int = 100,
) -> dict[str, Any]:
    results = await asyncio.gather(
        CisaKevCollector().collect(limit=kev_limit),
        NvdCollector().collect_recent(hours=48, limit=nvd_limit),
        GdeltCollector().search(
            query='("cyber attack" OR ransomware OR malware OR disinformation OR "information operation" OR "influence operation")',
            max_records=gdelt_limit,
        ),
        return_exceptions=True,
    )

    kev_result, nvd_result, gdelt_result = results
    kev = [] if isinstance(kev_result, Exception) else kev_result.get("records", [])
    nvd = [] if isinstance(nvd_result, Exception) else nvd_result.get("records", [])
    gdelt = [] if isinstance(gdelt_result, Exception) else gdelt_result.get("records", [])

    narratives = _information_products(gdelt)
    incidents = _priority_incidents(kev + nvd)
    exposures = _priority_exposures(kev)
    executive = _executive_judgment(kev, nvd, narratives)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assessment_version": "cyber-info-operational-overview-v1",
        "executive_judgment": executive,
        "source_health": [
            _source_status(kev_result, "cisa_kev"),
            _source_status(nvd_result, "nvd"),
            _source_status(gdelt_result, "gdelt"),
        ],
        "priority_incidents": incidents,
        "priority_vulnerabilities": exposures,
        "narrative_campaigns": narratives,
        "vendor_pressure": _vendor_pressure(kev),
        "cross_module_relevance": {
            "strategic_early_warning": bool(narratives or any(i.get("severity_score", 0) >= 80 for i in incidents)),
            "country_intelligence": bool(narratives),
            "supply_chain_intelligence": any(
                sector in {"energy", "transportation", "technology"}
                for item in narratives for sector in item.get("sectors", [])
            ),
            "corporate_financial_risk": any(
                sector in {"finance", "technology"}
                for item in narratives for sector in item.get("sectors", [])
            ),
        },
        "analytic_caveats": [
            "The overview uses live public-source collections and deterministic Phase 3/4 engines.",
            "Narrative coordination indicators do not prove orchestration, common control, falsity, or actor attribution.",
            "The posture score is an operational prioritization score, not a calibrated forecast probability.",
        ],
    }
