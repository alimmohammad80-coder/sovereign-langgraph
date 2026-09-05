from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


_TECHNIQUE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("public-facing", "internet-facing", "remote access", "vpn", "gateway", "sharepoint", "peoplesoft", "server-side request forgery", "authentication bypass", "missing authentication"), "T1190"),
    (("browser", "chromium", "chrome", "edge", "crafted html", "client execution"), "T1203"),
    (("command", "os commands", "command execution", "shell", "powershell", "scripting"), "T1059"),
    (("credential", "password", "account", "authentication"), "T1078"),
    (("phishing", "spearphishing", "malicious attachment", "malicious link"), "T1566"),
    (("exfiltration", "data theft", "steal documents", "sensitive data"), "T1041"),
    (("ransomware", "encrypt", "impact"), "T1486"),
)


def _text(*parts: Any) -> str:
    return " ".join(str(part or "") for part in parts).lower()


def _attack_index(records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_stix: dict[str, dict[str, Any]] = {}
    by_attack_id: dict[str, dict[str, Any]] = {}
    for record in records:
        stix_id = str(record.get("source_record_id") or "")
        attack_id = str(record.get("attack_id") or "")
        if stix_id:
            by_stix[stix_id] = record
        if attack_id:
            by_attack_id[attack_id] = record
    return by_stix, by_attack_id


def match_attack_techniques(
    *,
    incident: dict[str, Any],
    threat_context: dict[str, Any] | None,
    mitre_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    _, by_attack_id = _attack_index(mitre_records)
    context = threat_context or {}
    haystack = _text(
        incident.get("title"), incident.get("summary"), context.get("asset_role"),
        context.get("why_targeted"), " ".join(context.get("likely_attacker_objectives") or []),
    )
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for terms, attack_id in _TECHNIQUE_RULES:
        evidence = sorted({term for term in terms if term in haystack})
        if not evidence or attack_id in seen:
            continue
        official = by_attack_id.get(attack_id)
        if not official:
            continue
        matches.append({
            "attack_id": attack_id,
            "name": official.get("name"),
            "stix_id": official.get("source_record_id"),
            "tactics": [phase.get("phase_name") for phase in official.get("kill_chain_phases", []) if phase.get("phase_name")],
            "match_confidence": "moderate" if len(evidence) >= 2 else "low",
            "evidence_terms": evidence,
            "basis": "Deterministic semantic rule matched against the incident and verified against the official MITRE ATT&CK object.",
        })
        seen.add(attack_id)
    return matches


def correlate_attack_entities(
    *,
    technique_matches: list[dict[str, Any]],
    mitre_records: list[dict[str, Any]],
    limit: int = 6,
) -> dict[str, list[dict[str, Any]]]:
    by_stix, _ = _attack_index(mitre_records)
    technique_refs = {item.get("stix_id") for item in technique_matches if item.get("stix_id")}
    scores: dict[str, set[str]] = defaultdict(set)

    for record in mitre_records:
        raw = record.get("raw_stix") if isinstance(record.get("raw_stix"), dict) else {}
        if raw.get("type") != "relationship" or raw.get("relationship_type") != "uses":
            continue
        source_ref = str(raw.get("source_ref") or "")
        target_ref = str(raw.get("target_ref") or "")
        if target_ref in technique_refs:
            scores[source_ref].add(target_ref)

    groups: list[dict[str, Any]] = []
    campaigns: list[dict[str, Any]] = []
    for source_ref, matched_refs in scores.items():
        source = by_stix.get(source_ref)
        if not source:
            continue
        candidate = {
            "name": source.get("name") or source_ref,
            "stix_id": source_ref,
            "shared_technique_count": len(matched_refs),
            "shared_techniques": [
                next((item.get("attack_id") for item in technique_matches if item.get("stix_id") == ref), ref)
                for ref in sorted(matched_refs)
            ],
            "hypothesis_strength": "moderate" if len(matched_refs) >= 2 else "low",
            "analytic_caveat": "Technique overlap is not attribution. This candidate is shown only as a comparative hypothesis from MITRE ATT&CK usage relationships.",
        }
        if str(source_ref).startswith("intrusion-set--"):
            groups.append(candidate)
        elif str(source_ref).startswith("campaign--"):
            campaigns.append(candidate)

    groups.sort(key=lambda item: (-item["shared_technique_count"], item["name"]))
    campaigns.sort(key=lambda item: (-item["shared_technique_count"], item["name"]))
    return {"actor_hypotheses": groups[:limit], "campaign_hypotheses": campaigns[:limit]}


def build_indicator_relationships(incident: dict[str, Any]) -> list[dict[str, Any]]:
    relationships = []
    for indicator in incident.get("indicators") or []:
        value = indicator.get("value")
        kind = indicator.get("type")
        if not value:
            continue
        relationships.append({
            "relationship": "observed_indicator",
            "indicator_type": kind,
            "value": value,
            "confidence": "high",
            "evidence_status": "observed",
        })
    return relationships


def build_evidence_timeline(record: dict[str, Any], incident: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    provenance = record.get("provenance") or {}
    candidates = (
        (record.get("published") or provenance.get("published_at"), "source_publication", "Source record published or first documented."),
        (record.get("date_added"), "known_exploited_added", "Vulnerability added to the authoritative exploited-vulnerability catalog."),
        (record.get("last_modified"), "source_modified", "Source record materially updated."),
        (record.get("due_date"), "mitigation_due", "Required mitigation due date reported by the source."),
        (provenance.get("collected_at") or incident.get("observed_at"), "platform_collection", "Record collected by Sovereign Intelligence AI."),
    )
    for timestamp, event_type, summary in candidates:
        if not timestamp:
            continue
        events.append({"timestamp": str(timestamp), "event_type": event_type, "summary": summary, "evidence_status": "observed"})

    def sort_key(item: dict[str, Any]) -> str:
        raw = item.get("timestamp") or ""
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return raw

    return sorted(events, key=sort_key)


def build_alternative_hypotheses(record: dict[str, Any], threat_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    context = threat_context or {}
    hypotheses: list[dict[str, Any]] = []
    ransomware = str(record.get("known_ransomware_use") or "").lower() in {"known", "yes", "true"}
    asset_role = str(context.get("asset_role") or "")

    if ransomware:
        hypotheses.append({
            "hypothesis": "Financially motivated ransomware ecosystem activity",
            "confidence": "moderate",
            "supporting_evidence": ["Source reports known ransomware campaign use."],
            "contradictory_evidence": [],
        })
    if any(term in asset_role for term in ("remote-access", "enterprise", "business", "collaboration")):
        hypotheses.append({
            "hypothesis": "Initial-access or opportunistic enterprise intrusion activity",
            "confidence": "moderate" if record.get("record_type") == "known_exploited_vulnerability" else "low",
            "supporting_evidence": ["The affected technology can provide a foothold into enterprise environments."],
            "contradictory_evidence": [],
        })
    hypotheses.append({
        "hypothesis": "State-linked or espionage exploitation",
        "confidence": "low",
        "supporting_evidence": ["Strategic enterprise technologies are also commonly targeted for espionage."],
        "contradictory_evidence": ["No source-reported state actor attribution is available in the current record."],
    })
    return hypotheses[:4]


def enrich_investigation(
    *,
    record: dict[str, Any],
    incident: dict[str, Any],
    threat_context: dict[str, Any] | None,
    mitre_records: list[dict[str, Any]],
) -> dict[str, Any]:
    techniques = match_attack_techniques(incident=incident, threat_context=threat_context, mitre_records=mitre_records)
    correlations = correlate_attack_entities(technique_matches=techniques, mitre_records=mitre_records)
    indicators = build_indicator_relationships(incident)
    timeline = build_evidence_timeline(record, incident)
    hypotheses = build_alternative_hypotheses(record, threat_context)
    gaps = []
    if not techniques:
        gaps.append("MITRE ATT&CK technique mapping unresolved")
    if not indicators:
        gaps.append("No IOC or infrastructure indicators are present in the current source record")
    if not correlations["actor_hypotheses"]:
        gaps.append("No comparative actor candidates from current ATT&CK technique overlap")
    if not incident.get("countries"):
        gaps.append("Victim or exploitation geography unresolved")
    return {
        "attack_techniques": techniques,
        "actor_hypotheses": correlations["actor_hypotheses"],
        "campaign_hypotheses": correlations["campaign_hypotheses"],
        "indicator_relationships": indicators,
        "evidence_timeline": timeline,
        "alternative_hypotheses": hypotheses,
        "intelligence_gaps": gaps,
        "analytic_guardrail": "Named actor and campaign candidates derived from technique overlap are comparative hypotheses only and must not be presented as attribution without independent evidence.",
    }
