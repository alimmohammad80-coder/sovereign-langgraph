from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from app.intelligence.storage import get_supabase_client
from app.services.strategic_agents.nemotron_client import (
    NEMOTRON_MODEL,
    run_nemotron_text_analysis,
)


ReportType = Literal[
    "short_term",
    "long_term_fusion",
]


SECTOR_AGENT_KEYS = (
    "conflict_monitoring",
    "political_stability",
    "economic_risk",
    "energy_security",
    "trade_sanctions",
)


SECTOR_LABELS = {
    "conflict_monitoring": "Conflict and Security",
    "political_stability": "Political Stability",
    "economic_risk": "Economic Risk",
    "energy_security": "Energy Security",
    "trade_sanctions": "Trade and Sanctions",
}


METHODOLOGY_NAME = (
    "Sovereign Intelligence Analytical Methodology"
)
METHODOLOGY_VERSION = "SIAM-1.0-draft"
REPORTING_VERSION = "regional-reporting-v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client():
    client = get_supabase_client()

    if client is None:
        raise RuntimeError(
            "Supabase client is not configured."
        )

    return client


def _normalize_region(value: str) -> str:
    return " ".join(
        str(value or "").strip().split()
    )


def _load_latest_regional_output(
    *,
    agent_key: str,
    region: str,
) -> dict[str, Any] | None:
    """
    Load the newest authoritative assessment for an agent and region.

    Country-level rows may still exist during migration. They can
    contribute when their stored region matches the requested region.
    """
    result = (
        _client()
        .table("strategic_agent_outputs")
        .select("*")
        .eq("agent_key", agent_key)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    requested_region = _normalize_region(
        region
    ).lower()

    for row in result.data or []:
        row_region = _normalize_region(
            row.get("region") or ""
        ).lower()

        is_regional_output = (
            not row.get("country_iso3")
            and not row.get("country_name")
        )

        if (
            row_region == requested_region
            and is_regional_output
        ):
            return dict(row)

    return None


def _presentation_payload(
    row: dict[str, Any],
) -> dict[str, Any]:
    payload = row.get("presentation_payload")

    if isinstance(payload, dict):
        return payload

    return {}


def _compact_assessment(
    row: dict[str, Any],
) -> dict[str, Any]:
    payload = _presentation_payload(row)

    return {
        "sector": row.get("agent_key"),
        "sector_label": SECTOR_LABELS.get(
            str(row.get("agent_key")),
            str(row.get("agent_key")),
        ),
        "risk_score": row.get("risk_score"),
        "risk_level": row.get("risk_level"),
        "confidence": row.get("confidence"),
        "bluf": row.get("bluf"),
        "executive_summary": row.get(
            "executive_summary"
        ),
        "key_drivers": (
            row.get("key_drivers")
            or payload.get("key_drivers")
            or []
        )[:5],
        "forecast": (
            row.get("forecast_probabilities")
            or payload.get(
                "forecast_probabilities"
            )
            or {}
        ),
        "implications": (
            row.get("implications")
            or payload.get("implications")
            or []
        )[:4],
        "intelligence_gaps": (
            row.get("intelligence_gaps")
            or payload.get(
                "intelligence_gaps"
            )
            or []
        )[:4],
        "freshness_status": payload.get(
            "freshness_status"
        ),
        "latest_evidence_at": payload.get(
            "latest_evidence_at"
        ),
        "evidence_composition": payload.get(
            "evidence_composition"
        ) or {},
        "source_freshness": (
            payload.get("source_freshness")
            or []
        )[:20],
        "generated_at": (
            payload.get(
                "assessment_generated_at"
            )
            or row.get("created_at")
        ),
    }


def _build_regional_packet(
    *,
    region: str,
) -> dict[str, Any]:
    assessments = []

    for agent_key in SECTOR_AGENT_KEYS:
        row = _load_latest_regional_output(
            agent_key=agent_key,
            region=region,
        )

        if row is None:
            continue

        assessments.append(
            _compact_assessment(row)
        )

    if not assessments:
        raise ValueError(
            "No authoritative sector assessments "
            f"were found for region: {region}"
        )

    highest = max(
        assessments,
        key=lambda item: float(
            item.get("risk_score") or 0
        ),
    )

    confidence_values = [
        float(item.get("confidence") or 0)
        for item in assessments
        if item.get("confidence") is not None
    ]

    average_confidence = (
        sum(confidence_values)
        / len(confidence_values)
        if confidence_values
        else 0
    )

    total_evidence = 0
    live_signals = 0
    recent_indicators = 0
    structural_indicators = 0

    for assessment in assessments:
        composition = (
            assessment.get(
                "evidence_composition"
            )
            or {}
        )

        total_evidence += int(
            composition.get(
                "total_evidence",
                0,
            )
            or 0
        )
        live_signals += int(
            composition.get(
                "live_signals",
                0,
            )
            or 0
        )
        recent_indicators += int(
            composition.get(
                "recent_indicators",
                0,
            )
            or 0
        )
        structural_indicators += int(
            composition.get(
                "structural_indicators",
                0,
            )
            or 0
        )

    return {
        "region": region,
        "coverage": {
            "expected_sectors": len(
                SECTOR_AGENT_KEYS
            ),
            "available_sectors": len(
                assessments
            ),
            "missing_sectors": [
                SECTOR_LABELS[key]
                for key in SECTOR_AGENT_KEYS
                if key not in {
                    item.get("sector")
                    for item in assessments
                }
            ],
        },
        "regional_risk": {
            "leading_sector": highest.get(
                "sector_label"
            ),
            "highest_risk_score": highest.get(
                "risk_score"
            ),
            "highest_risk_level": highest.get(
                "risk_level"
            ),
            "average_confidence": round(
                average_confidence,
                2,
            ),
        },
        "evidence_composition": {
            "live_signals": live_signals,
            "recent_indicators": (
                recent_indicators
            ),
            "structural_indicators": (
                structural_indicators
            ),
            "total_evidence": total_evidence,
        },
        "sector_assessments": assessments,
    }


def _short_term_prompt(
    *,
    region: str,
    evidence_packet: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = """
You are the senior regional intelligence analyst for Sovereign
Intelligence AI.

Prepare a brief, forward-looking regional analytical report.

Use only the supplied authoritative sector assessments. Connect recent
events and signals to structural conditions, but focus on what is likely
to happen next over the coming 7, 30, and 90 days.

Write for senior decision-makers.

Requirements:

- Lead with a clear judgment.
- Explain what is changing and why it matters.
- Distinguish current developments from long-term baseline conditions.
- Identify the three to five most important drivers.
- Explain likely regional spillovers.
- State what could alter the trajectory.
- Treat missing current evidence as an intelligence gap.
- Do not invent events, figures, sources, probabilities, or causal links.
- Do not recalculate supplied risk or confidence scores.
- Avoid jargon, clichés, academic language, repetition, and filler.
- Keep the report brief and easy to scan.
- Return professional Markdown, not JSON.
""".strip()

    user_prompt = f"""
Region: {region}

Authoritative regional evidence:
{json.dumps(
    evidence_packet,
    ensure_ascii=False,
    default=str,
)}

Write the report using exactly these headings:

# {region}: Short-Term Analytical Report

## BLUF

One sentence, maximum 35 words.

## Regional Judgment

One short paragraph explaining what is changing, why it matters, and
the most likely near-term direction.

## Key Drivers

Three to five concise bullets.

## Forward Outlook

### 7 Days

One concise judgment.

### 30 Days

One concise judgment.

### 90 Days

One concise judgment.

## What We Are Watching

Four to six specific indicators or triggers.

## Confidence and Intelligence Gaps

One short paragraph explaining confidence, source limitations, and the
most important unresolved question.
""".strip()

    return system_prompt, user_prompt


def _long_term_prompt(
    *,
    region: str,
    evidence_packet: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = """
You are the senior regional fusion analyst for Sovereign Intelligence AI.

Prepare a forward-looking regional fusion report that connects current
developments with structural political, security, economic, energy,
trade, sanctions, market, and supply-chain conditions.

The report is for strategic planning, not news summarization.

Requirements:

- Explain which current developments are temporary and which may produce
  structural change.
- Assess regional actors, alignments, dependencies, and vulnerabilities.
- Identify supported cross-sector effects and causal pathways.
- Provide 6-, 12-, and 24-month outlooks.
- Describe the longer-term strategic trajectory over three to five years.
- Include alternative outcomes and severe but plausible shock scenarios.
- Explain what indicators would confirm or invalidate the assessment.
- Do not invent events, figures, sources, probabilities, or relationships.
- Do not recalculate supplied deterministic scores.
- Treat intelligence gaps explicitly.
- Avoid jargon, clichés, academic prose, alarmism, and unnecessary length.
- Return professional Markdown, not JSON.
""".strip()

    user_prompt = f"""
Region: {region}

Authoritative regional evidence:
{json.dumps(
    evidence_packet,
    ensure_ascii=False,
    default=str,
)}

Write the report using exactly these headings:

# {region}: Long-Term Fusion Report

## BLUF

One sentence, maximum 35 words.

## Executive Judgment

One concise paragraph.

## Regional Strategic Direction

Explain the main regional trajectory.

## Structural Baseline

Explain the slower-moving political, security, economic, energy, trade,
technology, alliance, and supply-chain conditions that matter most.

## Short-Term Developments with Long-Term Significance

Explain which current developments could materially alter the regional
trajectory and which appear temporary.

## Regional Actors and Alignments

Explain relevant state, alliance, institutional, and non-state dynamics.

## Dependencies and Vulnerabilities

Explain the region's critical dependencies, constraints, and resilience.

## Cross-Sector Effects

Explain supported links between security, politics, economics, energy,
trade, sanctions, markets, and supply chains.

## Strategic Outlook

### 6 Months

One concise judgment.

### 12 Months

One concise judgment.

### 24 Months

One concise judgment.

### 3–5 Years

One concise strategic trajectory.

## Alternative Outcomes

Two or three credible alternatives.

## Shock Scenarios

Two or three severe but plausible scenarios with triggering conditions.

## What We Are Watching

Five to eight specific indicators.

## Intelligence Gaps and Confidence

One concise paragraph.
""".strip()

    return system_prompt, user_prompt


def generate_regional_report(
    *,
    region: str,
    report_type: ReportType,
) -> dict[str, Any]:
    clean_region = _normalize_region(region)

    if not clean_region:
        raise ValueError(
            "A region is required."
        )

    evidence_packet = _build_regional_packet(
        region=clean_region,
    )

    if report_type == "short_term":
        system_prompt, user_prompt = (
            _short_term_prompt(
                region=clean_region,
                evidence_packet=evidence_packet,
            )
        )
        max_tokens = 1800

    elif report_type == "long_term_fusion":
        system_prompt, user_prompt = (
            _long_term_prompt(
                region=clean_region,
                evidence_packet=evidence_packet,
            )
        )
        max_tokens = 3200

    else:
        raise ValueError(
            f"Unsupported report type: {report_type}"
        )

    report_content = run_nemotron_text_analysis(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.15,
        max_tokens=max_tokens,
    )

    return {
        "status": "success",
        "report_type": report_type,
        "region": clean_region,
        "title": (
            f"{clean_region} "
            + (
                "Short-Term Analytical Report"
                if report_type == "short_term"
                else "Long-Term Fusion Report"
            )
        ),
        "content_format": "markdown",
        "content": report_content,
        "deterministic_summary": (
            evidence_packet["regional_risk"]
        ),
        "coverage": evidence_packet["coverage"],
        "evidence_composition": (
            evidence_packet[
                "evidence_composition"
            ]
        ),
        "methodology": {
            "name": METHODOLOGY_NAME,
            "version": METHODOLOGY_VERSION,
        },
        "analysis_provenance": {
            "provider": "nvidia",
            "model": NEMOTRON_MODEL,
            "status": "completed",
            "generated_at": utc_now_iso(),
        },
        "reporting_version": REPORTING_VERSION,
    }
