from __future__ import annotations

import re
from typing import Any

from .confidence import assess_confidence
from .models import EvidenceStatus, SourceProvenance
from .phase3_models import (
    ActorCampaignLink,
    CyberIncident,
    CyberIncidentType,
    ExposureLevel,
    InfrastructureTargetProfile,
    VulnerabilityExposure,
)


_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.I)


def _provenance(record: dict[str, Any]) -> list[SourceProvenance]:
    raw = record.get("provenance")
    if not isinstance(raw, dict):
        return []
    return [SourceProvenance.model_validate(raw)]


def _confidence(record: dict[str, Any], *, corroborated: bool = False):
    reliability = float((record.get("provenance") or {}).get("reliability_score") or 0.65)
    return assess_confidence(
        evidence_quality=min(1.0, max(0.0, reliability)),
        source_diversity=0.75 if corroborated else 0.35,
        corroboration=0.8 if corroborated else 0.45,
        analytic_uncertainty=0.2 if corroborated else 0.35,
        rationale="Deterministic Phase 3 confidence from source reliability, corroboration, and analytic uncertainty.",
    )


def _level(score: float) -> ExposureLevel:
    if score >= 85:
        return ExposureLevel.CRITICAL
    if score >= 70:
        return ExposureLevel.HIGH
    if score >= 55:
        return ExposureLevel.ELEVATED
    if score >= 35:
        return ExposureLevel.GUARDED
    return ExposureLevel.LOW


class CyberIntelligenceEngine:
    """Convert normalized Phase 2 collector records into operational cyber intelligence."""

    def incident_from_record(self, record: dict[str, Any]) -> CyberIncident:
        source = str(record.get("source") or "unknown")
        record_type = str(record.get("record_type") or "unknown")
        text = " ".join(str(record.get(k) or "") for k in ("title", "description", "threat", "required_action"))
        cves = sorted(set(_CVE_RE.findall(text) + ([str(record.get("source_record_id"))] if str(record.get("source_record_id", "")).upper().startswith("CVE-") else [])))

        incident_type = CyberIncidentType.UNKNOWN
        if record_type in {"known_exploited_vulnerability", "vulnerability"}:
            incident_type = CyberIncidentType.EXPLOITATION if record_type == "known_exploited_vulnerability" else CyberIncidentType.VULNERABILITY_DISCLOSURE
        elif record_type == "malware_distribution_infrastructure":
            incident_type = CyberIncidentType.MALWARE_ACTIVITY
        elif record_type in {"cybersecurity_advisory", "cert_advisory"}:
            incident_type = CyberIncidentType.ADVISORY
        elif record_type in {"ip_reputation", "indicator"}:
            incident_type = CyberIncidentType.INFRASTRUCTURE_ABUSE

        severity = 40.0
        if record_type == "known_exploited_vulnerability":
            severity = 78.0
        if str(record.get("known_ransomware_use") or "").lower() in {"known", "yes", "true"}:
            severity = max(severity, 88.0)
        abuse = record.get("abuse_confidence_score")
        if isinstance(abuse, (int, float)):
            severity = max(severity, float(abuse))
        if record_type == "malware_distribution_infrastructure" and record.get("url_status") == "online":
            severity = max(severity, 72.0)

        title = str(record.get("title") or record.get("name") or record.get("source_record_id") or record_type)
        summary = str(record.get("description") or record.get("info") or record.get("threat") or title)
        indicators = []
        for key, kind in (("url", "url"), ("ip_address", "ip"), ("host", "host")):
            if record.get(key):
                indicators.append({"type": kind, "value": record[key]})

        return CyberIncident(
            incident_type=incident_type,
            title=title,
            summary=summary,
            source=source,
            source_record_id=str(record.get("source_record_id") or "") or None,
            cves=cves,
            indicators=indicators,
            sectors=[str(record["sector"])] if record.get("sector") else [],
            severity_score=min(100.0, severity),
            confidence=_confidence(record),
            provenance=_provenance(record),
            metadata={"source_record_type": record_type, "raw_source": source},
        )

    def vulnerability_exposure(
        self,
        record: dict[str, Any],
        *,
        target_criticality_score: float = 50.0,
    ) -> VulnerabilityExposure:
        cve_id = str(record.get("source_record_id") or record.get("cve_id") or "")
        if not cve_id.upper().startswith("CVE-"):
            raise ValueError("vulnerability exposure requires a CVE record")

        known_exploited = record.get("record_type") == "known_exploited_vulnerability"
        ransomware = str(record.get("known_ransomware_use") or "").lower() in {"known", "yes", "true"}
        severity = 80.0 if known_exploited else 55.0
        exploitability = 95.0 if known_exploited else 50.0
        if ransomware:
            exploitability = 100.0
            severity = max(severity, 90.0)

        score = round(0.4 * severity + 0.35 * exploitability + 0.25 * target_criticality_score, 1)
        rationale = ["Known exploitation confirmed by source." if known_exploited else "No confirmed exploitation in this record."]
        if ransomware:
            rationale.append("Known ransomware campaign use reported.")
        rationale.append(f"Target criticality input: {target_criticality_score:.0f}/100.")

        return VulnerabilityExposure(
            cve_id=cve_id.upper(),
            vendor=record.get("vendor"),
            product=record.get("product"),
            known_exploited=known_exploited,
            known_ransomware_use=ransomware,
            exposure_score=score,
            exposure_level=_level(score),
            severity_score=severity,
            exploitability_score=exploitability,
            target_criticality_score=target_criticality_score,
            evidence_status=EvidenceStatus.OBSERVED,
            confidence=_confidence(record),
            provenance=_provenance(record),
            rationale=rationale,
        )

    def actor_campaign_link(self, record: dict[str, Any]) -> ActorCampaignLink | None:
        raw = record.get("raw_stix") if isinstance(record.get("raw_stix"), dict) else record
        if raw.get("type") != "relationship":
            return None
        source_ref = str(raw.get("source_ref") or "")
        target_ref = str(raw.get("target_ref") or "")
        if not source_ref or not target_ref:
            return None
        return ActorCampaignLink(
            actor_name=source_ref,
            campaign_name=target_ref,
            relationship=str(raw.get("relationship_type") or "associated_with"),
            evidence_status=EvidenceStatus.OBSERVED,
            confidence=_confidence(record),
            supporting_sources=[str(record.get("source") or "mitre_attack")],
        )

    def infrastructure_target_profile(
        self,
        *,
        name: str,
        sector: str,
        country_iso3: str | None,
        criticality_score: float,
        incidents: list[CyberIncident],
    ) -> InfrastructureTargetProfile:
        relevant = [i for i in incidents if not i.sectors or sector in i.sectors]
        cves = sorted({c for i in relevant for c in i.cves})
        actors = sorted({a for i in relevant for a in i.suspected_actors})
        campaigns = sorted({c for i in relevant for c in i.campaign_names})
        avg_severity = sum(i.severity_score for i in relevant) / len(relevant) if relevant else 0.0
        targeting_score = round(min(100.0, 0.55 * criticality_score + 0.30 * avg_severity + 5 * min(len(relevant), 3)), 1)
        confidence = assess_confidence(
            evidence_quality=0.75 if relevant else 0.45,
            source_diversity=min(1.0, len({i.source for i in relevant}) / 3) if relevant else 0.2,
            corroboration=0.75 if len(relevant) >= 2 else 0.4,
            analytic_uncertainty=0.25 if relevant else 0.5,
            rationale="Targeting profile derived deterministically from incident volume, severity, source diversity, and asset criticality.",
        )
        return InfrastructureTargetProfile(
            name=name,
            sector=sector,
            country_iso3=country_iso3,
            criticality_score=criticality_score,
            observed_incident_count=len(relevant),
            vulnerability_ids=cves,
            actor_names=actors,
            campaign_names=campaigns,
            targeting_score=targeting_score,
            confidence=confidence,
        )
