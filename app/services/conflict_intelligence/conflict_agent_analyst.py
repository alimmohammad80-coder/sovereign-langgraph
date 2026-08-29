from __future__ import annotations

import json
from typing import Any

from app.ai_gateway import (
    AIGatewayRequest,
    AIResponseFormat,
    AITaskType,
    get_ai_gateway,
)


AGENT_SYSTEM_PROMPT = """
You are the Conflict Intelligence Analyst for Sovereign Intelligence AI.

You receive a governed intelligence packet assembled by the
Conflict Intelligence Agent.

The packet may include:

- user-selected countries
- region
- conflict type
- indicators
- baseline conflict/history data
- current observations
- current evidence/news
- canonical conflict context when available
- deterministic forecast/model results when available

RULES

The supplied data and deterministic model outputs are authoritative.

Never invent:
- probabilities
- percentages
- confidence scores
- event counts
- casualty numbers
- historical statistics
- sources
- citations

If deterministic model outputs are available, preserve them.

If deterministic quantitative outputs are unavailable, provide a
qualitative assessment and explicitly state that a calibrated numeric
forecast was not available.

Do not refuse analysis merely because no canonical conflict_id exists.

Separate:
1. observed evidence
2. historical/baseline context
3. deterministic model output
4. analytic judgment
5. uncertainty

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

key_drivers must be an array of objects:
{
  "driver": "...",
  "assessment": "...",
  "evidence_refs": []
}

contrary_evidence must be an array.

forecast_outlook must contain:
{
  "near_term": "...",
  "medium_term": "...",
  "long_term": "..."
}

references must be an array.

full_analysis should be a polished executive intelligence assessment,
approximately 800-1200 words when sufficient evidence exists.
""".strip()


class ConflictAgentAnalyst:

    ANALYST_VERSION = (
        "conflict-agent-analyst-v1"
    )

    REQUIRED_KEYS = {
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

    def __init__(self) -> None:
        self.gateway = get_ai_gateway()

    def analyze(
        self,
        packet: dict[str, Any],
        *,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> dict[str, Any]:

        response = self.gateway.generate(
            AIGatewayRequest(
                task_type=
                    AITaskType.FULL_ANALYSIS,

                system_prompt=
                    AGENT_SYSTEM_PROMPT,

                user_prompt=
                    json.dumps(
                        packet,
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

                max_tokens=12000,

                metadata={
                    "analyst_version":
                        self.ANALYST_VERSION,

                    "required_json_keys":
                        sorted(
                            self.REQUIRED_KEYS
                        ),

                    "packet_version":
                        packet.get(
                            "packet_version"
                        ),
                },
            )
        )

        payload = response.parsed_json

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "AI analyst did not return "
                "a JSON object."
            )

        missing = (
            self.REQUIRED_KEYS
            - set(payload.keys())
        )

        if missing:
            raise ValueError(
                "AI analyst response missing keys: "
                + ", ".join(
                    sorted(missing)
                )
            )

        return {
            "provider":
                response.provider,

            "model":
                response.model,

            "analyst_version":
                self.ANALYST_VERSION,

            "packet_version":
                packet.get(
                    "packet_version"
                ),

            "report":
                payload,
        }
