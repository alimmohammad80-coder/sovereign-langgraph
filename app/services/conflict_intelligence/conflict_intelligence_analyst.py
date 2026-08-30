from __future__ import annotations

import json
from typing import Any

from app.ai_gateway import (
    AIGatewayRequest,
    AIResponseFormat,
    AITaskType,
    get_ai_gateway,
)

from app.services.conflict_intelligence.analysis_packet_builder import (
    ConflictAnalysisPacketBuilder,
)

from app.services.conflict_intelligence.conflict_analysis_validator import (
    ConflictAnalysisValidator,
)

from app.services.conflict_intelligence.conflict_report_persistence import (
    ConflictReportPersistence,
)

from app.services.conflict_intelligence.report_presentation import (
    prepare_report_for_presentation,
)


SYSTEM_PROMPT = """
You are the Conflict Intelligence Analyst for Sovereign Intelligence AI.

You receive a structured conflict-analysis packet containing:

- historical conflict context
- current evidence
- source citations
- deterministic/statistical forecast outputs
- model applicability
- ripple effects

The quantitative forecasting system is authoritative.

GROUNDING RULES

- The field current_state_escalation_probability belongs to
  conflict-state-v1. Never call it a Markov probability.
- Markov forecasts are only the distributions contained in the
  horizons model output.
- Do not calculate or invent historical recurrence counts.
- Use historical_state_counts exactly as supplied.
- Do not derive an "event count", "war count", recurrence frequency,
  or historical rate unless that value is explicitly supplied.
- Preserve every numerical probability exactly to reasonable rounding.
- NEVER invent, estimate, derive, average, interpolate, or calculate a new percentage.
- Every percentage written in the report must already exist explicitly in the supplied analysis packet.
- The packet contains a field named allowed_percentage_values.
- That list is the ONLY whitelist of percentages you may use.
- Never invent, interpolate, average, estimate, derive, or round a new percentage that is not already contained in allowed_percentage_values.
- The packet contains allowed_percentage_values. This is the authoritative whitelist for percentage claims.
- NEVER write a percentage that is not represented in allowed_percentage_values.
- If a percentage is not explicitly present in the packet, describe the assessment qualitatively instead.
- Do not convert historical counts, durations, ratios, or narrative judgments into percentages.
- Do not create confidence percentages unless the exact confidence value is supplied.

You MUST NOT:
- recalculate probabilities
- replace model probabilities
- invent sources
- invent events
- invent historical facts
- invent contrary evidence
- claim certainty unsupported by the packet

Your task is to produce a highly contextual, analytically rigorous,
professional intelligence assessment that is enjoyable to read.

Clearly distinguish:

1. observed evidence
2. historical context
3. quantitative model output
4. analytic inference

Use plain professional language. Avoid excessive technical jargon.

If statistical models disagree, explain the disagreement in substantive
terms without changing their outputs.

If contrary or de-escalatory evidence is absent, explicitly state that
none was identified in the supplied evidence set. Do not manufacture it.

CITATIONS

Use the supplied citation_text fields.

Use Chicago Notes and Bibliography style.

Every important factual or historical claim should be supported by an
available citation whenever possible.

Use numbered citation markers in the prose:

[1]
[2]
[3]

The references array must map those numbers to the supplied sources.

Do not cite internal model outputs as external sources. Model outputs
should instead be described as Sovereign Intelligence AI model results.

OUTPUT

Return valid JSON only with exactly these keys:

bluf
executive_judgment
current_situation
key_drivers
contrary_evidence
historical_context
escalation_pathways
forecast_outlook
indicators_to_watch
strategic_implications
confidence_assessment
full_analysis
references

Requirements:

bluf:
One concise paragraph, maximum 6 sentences.

executive_judgment:
A concise analytic judgment explaining the overall risk picture.

current_situation:
2-4 substantive paragraphs based on current evidence.

key_drivers:
Array of objects with:
- driver
- assessment
- evidence_refs

contrary_evidence:
Array of objects with:
- factor
- assessment
- evidence_refs

If none exists, return [].

historical_context:
Explain how current conditions compare with the supplied historical record.
Do not force historical analogies.

escalation_pathways:
Array of plausible pathways, not predictions of certainty.

forecast_outlook:
Object with:
- near_term
- medium_term
- long_term

Use the supplied quantitative forecast horizons.
Do not change their probabilities.

indicators_to_watch:
Array of concrete observable indicators.

strategic_implications:
Discuss regional security, diplomatic, economic, and relevant spillover effects.

confidence_assessment:
Explain confidence based on evidence quantity, evidence quality,
historical coverage, and model agreement/disagreement.

full_analysis:
Approximately 800-1200 words.
Write as a polished strategic intelligence assessment.

references:
Array of objects:
- number
- citation
- source_name
- source_url
""".strip()


class ConflictIntelligenceAnalyst:

    ANALYST_VERSION = "conflict-intelligence-analyst-v1"

    def __init__(self) -> None:
        self.gateway = get_ai_gateway()
        self.packet_builder = (
            ConflictAnalysisPacketBuilder()
        )

        self.validator = (
            ConflictAnalysisValidator()
        )

        self.persistence = (
            ConflictReportPersistence()
        )

    @staticmethod
    def _compact_packet(
        packet: dict[str, Any],
    ) -> dict[str, Any]:

        evidence = packet.get(
            "current_evidence"
        ) or {}

        return {
            "packet_version":
                packet.get(
                    "packet_version"
                ),

            "conflict_id":
                packet.get(
                    "conflict_id"
                ),

            "conflict":
                packet.get(
                    "conflict"
                ),

            "historical_context":
                packet.get(
                    "historical_context"
                ),

            "current_evidence": {
                "observation_count":
                    evidence.get(
                        "observation_count"
                    ),

                "evidence_count":
                    evidence.get(
                        "evidence_count"
                    ),

                "event_type_counts":
                    evidence.get(
                        "event_type_counts"
                    ),

                "strongest_escalatory":
                    evidence.get(
                        "strongest_escalatory"
                    )
                    or [],

                "strongest_contrary":
                    evidence.get(
                        "strongest_contrary"
                    )
                    or [],

                "strongest_neutral":
                    evidence.get(
                        "strongest_neutral"
                    )
                    or [],
            },

            "authoritative_metrics":
                packet.get(
                    "authoritative_metrics"
                ),

            "forecast_models":
                packet.get(
                    "forecast_models"
                ),

            "ripple":
                packet.get(
                    "ripple"
                ),

            "sources":
                packet.get(
                    "sources"
                )
                or [],

            "analysis_rules":
                packet.get(
                    "analysis_rules"
                ),
        }

    def analyze(
        self,
        *,
        conflict_id: int,
        horizon_days: int = 365,
        lookback_days: int = 90,
        ripple_depth: int = 3,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> dict[str, Any]:

        packet = (
            self.packet_builder.build(
                conflict_id=conflict_id,
                horizon_days=horizon_days,
                lookback_days=lookback_days,
                ripple_depth=ripple_depth,
            )
        )

        compact_packet = (
            self._compact_packet(
                packet
            )
        )

        allowed_percentage_values = sorted(
            self.validator._packet_probabilities(
                packet
            )
        )

        compact_packet[
            "allowed_percentage_values"
        ] = allowed_percentage_values

        required = {
            "bluf",
            "executive_judgment",
            "current_situation",
            "key_drivers",
            "contrary_evidence",
            "historical_context",
            "escalation_pathways",
            "forecast_outlook",
            "indicators_to_watch",
            "strategic_implications",
            "confidence_assessment",
            "full_analysis",
            "references",
        }

        response = self.gateway.generate(
            AIGatewayRequest(
                task_type=
                    AITaskType.FULL_ANALYSIS,

                system_prompt=
                    SYSTEM_PROMPT,

                user_prompt=
                    json.dumps(
                        compact_packet,
                        ensure_ascii=False,
                        default=str,
                    ),

                preferred_provider=
                    preferred_provider,

                preferred_model=
                    preferred_model,

                response_format=
                    AIResponseFormat.JSON,

                temperature=0.2,

                # Full executive products need enough output
                # room for all required sections and long-form
                # analysis.
                max_tokens=12000,

                metadata={
                    "conflict_id":
                        conflict_id,

                    "analyst_version":
                        self.ANALYST_VERSION,

                    "packet_version":
                        packet.get(
                            "packet_version"
                        ),

                    "required_json_keys":
                        sorted(required),
                },
            )
        )

        payload = (
            response.parsed_json
            if isinstance(
                response.parsed_json,
                dict,
            )
            else json.loads(
                response.content
            )
        )

        missing = (
            required
            - set(
                payload.keys()
            )
        )

        if missing:
            raise ValueError(
                "AI analyst response missing keys: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )

        qa = self.validator.validate(
            report=payload,
            packet=packet,
        )

        if not qa["passed"]:
            raise ValueError(
                "Conflict intelligence analysis failed QA: "
                + json.dumps(
                    qa,
                    ensure_ascii=False,
                    default=str,
                )
            )

        presentation_report, assessment_mode = (
            prepare_report_for_presentation(
                payload,
                packet=packet,
            )
        )

        provider = getattr(
            response,
            "provider",
            None,
        )

        model = getattr(
            response,
            "model",
            None,
        )

        persisted_report = (
            self.persistence.persist(
                conflict_id=conflict_id,
                analyst_version=
                    self.ANALYST_VERSION,
                packet_version=
                    packet.get(
                        "packet_version"
                    )
                    or "unknown",
                provider=provider,
                model=model,
                report=presentation_report,
                qa=qa,
            )
        )

        return {
            "conflict_id":
                conflict_id,

            "analyst_version":
                self.ANALYST_VERSION,

            "provider":
                provider,

            "model":
                model,

            "qa":
                qa,

            "persisted":
                True,

            "report_id":
                persisted_report.get(
                    "id"
                ),

            "report_key":
                persisted_report.get(
                    "report_key"
                ),

            "assessment_mode":
                assessment_mode.value,

            "report":
                presentation_report,

            "packet_summary": {
                "historical_timeline_count":
                    packet[
                        "historical_context"
                    ][
                        "timeline_count"
                    ],

                "evidence_count":
                    packet[
                        "current_evidence"
                    ][
                        "evidence_count"
                    ],

                "source_count":
                    len(
                        packet[
                            "sources"
                        ]
                    ),
            },
        }
