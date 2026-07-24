from __future__ import annotations

from typing import Any

from app.agents.base_agent import (
    AgentAssessment,
    AgentSignal,
    BaseStrategicAgent,
)
from app.services.strategic_agents.live_political_collector import (
    collect_live_political_signals,
)
from app.services.strategic_agents.nemotron_client import (
    nemotron_configured,
    run_nemotron_analysis,
)


class PoliticalStabilityAgent(BaseStrategicAgent):
    agent_key = "political_stability"
    domain = "political"

    async def collect_signals(
        self,
        context: dict[str, Any],
    ) -> list[AgentSignal]:
        supplied_signals = context.get("signals", [])

        if not supplied_signals:
            signal_limit = int(
                context.get("signal_limit", 25)
            )

            live_signals = (
                await collect_live_political_signals(
                    country_name=context.get(
                        "country_name"
                    ),
                    country_iso3=context.get(
                        "country_iso3"
                    ),
                    region=context.get("region"),
                    limit=signal_limit,
                )
            )

            combined = list(live_signals)

            deduplicated: list[AgentSignal] = []
            seen: set[str] = set()

            for signal in combined:
                identity = (
                    signal.evidence_url
                    or signal.headline
                    or signal.signal_id
                ).strip().lower()

                if identity in seen:
                    continue

                seen.add(identity)
                deduplicated.append(signal)

            return deduplicated[:signal_limit]

        normalized: list[AgentSignal] = []

        for index, item in enumerate(supplied_signals):
            normalized.append(
                AgentSignal(
                    signal_id=str(
                        item.get("signal_id")
                        or item.get("id")
                        or f"manual-political-{index}"
                    ),
                    domain="political",
                    signal_type=str(
                        item.get(
                            "signal_type",
                            "political_stability_event",
                        )
                    ),
                    headline=str(
                        item.get(
                            "headline",
                            "Untitled political signal",
                        )
                    ),
                    summary=item.get("summary"),
                    country_iso3=item.get("country_iso3"),
                    country_name=item.get("country_name"),
                    region=item.get("region"),
                    severity=float(item.get("severity", 0)),
                    relevance=float(item.get("relevance", 50)),
                    confidence=float(item.get("confidence", 50)),
                    source_reliability=float(
                        item.get("source_reliability", 50)
                    ),
                    materiality_score=float(
                        item.get("materiality_score", 0)
                    ),
                    direction=str(item.get("direction", "neutral")),
                    event_time=item.get("event_time"),
                    source_key=item.get("source_key"),
                    evidence_url=item.get("evidence_url"),
                )
            )

        return normalized

    async def analyze(
        self,
        signals: list[AgentSignal],
        context: dict[str, Any],
    ) -> AgentAssessment:
        if not signals:
            return AgentAssessment(
                agent_key=self.agent_key,
                title="Political Stability Assessment",
                bluf=(
                    "No material political-stability signals were available "
                    "for the current assessment cycle."
                ),
                executive_summary=(
                    "The agent completed successfully but did not identify "
                    "sufficient current evidence of elevated political stress."
                ),
                risk_score=0,
                risk_level="Low",
                confidence=25,
                analytical_status="nominal",
                key_drivers=[],
                indicators=[],
                forecast_probabilities={
                    "7d": 5,
                    "30d": 10,
                    "90d": 15,
                    "180d": 20,
                },
                implications=["Continue routine political monitoring."],
                recommendations=[
                    "Refresh political, election, and protest sources."
                ],
                intelligence_gaps=[
                    "No current normalized political signals were available."
                ],
                related_signal_ids=[],
                country_iso3=context.get("country_iso3"),
                country_name=context.get("country_name"),
                region=context.get("region"),
            )

        # Political risk magnitude should be driven primarily by
        # observed severity. Evidence quality affects trust and
        # materiality, but should not independently manufacture risk.
        weighted_scores = [
            signal.severity * 0.65
            + signal.materiality_score * 0.35
            for signal in signals
        ]

        weighted_scores.sort(reverse=True)
        strongest = weighted_scores[:10]
        base_score = sum(strongest) / len(strongest)

        deteriorating = sum(
            1 for signal in signals
            if signal.direction == "deteriorating"
        )
        improving = sum(
            1 for signal in signals
            if signal.direction == "improving"
        )

        risk_score = self.clamp_score(
            base_score
            + min(12, deteriorating * 2)
            - min(8, improving * 2)
        )

        confidence = self.clamp_score(
            sum(signal.confidence for signal in signals)
            / len(signals)
        )

        priority_signals = sorted(
            signals,
            key=lambda item: (
                item.materiality_score,
                item.severity,
                item.confidence,
            ),
            reverse=True,
        )[:5]

        key_drivers = [
            {
                "headline": signal.headline,
                "severity": signal.severity,
                "confidence": signal.confidence,
                "country_iso3": signal.country_iso3,
                "source_key": signal.source_key,
                "direction": signal.direction,
            }
            for signal in priority_signals
        ]

        indicators = [
            {
                "name": signal.signal_type,
                "value": signal.severity,
                "direction": signal.direction,
            }
            for signal in priority_signals
        ]

        probability_7d = self.clamp_score(risk_score * 0.72)
        probability_30d = self.clamp_score(risk_score * 0.90)
        probability_90d = self.clamp_score(risk_score + 4)
        probability_180d = self.clamp_score(risk_score + 8)

        default_bluf = (
            f"Political stability risk is assessed as "
            f"{self.risk_level(risk_score).lower()} with a score "
            f"of {risk_score:.0f}/100."
        )
        default_summary = (
            f"The agent evaluated {len(signals)} political-stability "
            f"signals and identified the most material drivers of "
            f"institutional and government stress."
        )
        implications = [
            "Political uncertainty may affect governance continuity.",
            "Institutional stress could spill over into economic and security risk.",
        ]
        recommendations = [
            "Monitor the highest-materiality political indicators.",
            "Cross-check election, protest, and government continuity signals.",
        ]
        intelligence_gaps = [
            "Some political developments may lack independent corroboration."
        ]

        bluf = default_bluf
        executive_summary = default_summary

        if nemotron_configured():
            try:
                evidence = [
                    {
                        "headline": signal.headline,
                        "summary": signal.summary,
                        "severity": signal.severity,
                        "confidence": signal.confidence,
                        "direction": signal.direction,
                        "source_key": signal.source_key,
                    }
                    for signal in priority_signals
                ]

                result = run_nemotron_analysis(
                    system_prompt=(
                        "You are a senior political-risk analyst. "
                        "Use only the supplied evidence. Distinguish observed "
                        "facts from analytical inference. Do not infer coup, "
                        "government collapse, election fraud, or regime failure "
                        "unless directly supported. Use calibrated estimative "
                        "language. Do not recalculate the deterministic score. "
                        "Return valid JSON only."
                    ),
                    user_prompt=(
                        f"Deterministic political risk score: {risk_score}\n"
                        f"Risk level: {self.risk_level(risk_score)}\n"
                        f"Confidence: {confidence}\n"
                        f"Forecasts: 7d={probability_7d}, "
                        f"30d={probability_30d}, "
                        f"90d={probability_90d}, "
                        f"180d={probability_180d}\n"
                        f"Evidence: {evidence}\n\n"
                        "Return exactly this JSON structure:\n"
                        "{\n"
                        '  "bluf": "one concise strategic judgment",\n'
                        '  "executive_summary": "one short paragraph",\n'
                        '  "implications": ["one", "two"],\n'
                        '  "recommendations": ["one", "two"],\n'
                        '  "intelligence_gaps": ["one"]\n'
                        "}"
                    ),
                    max_tokens=1200,
                )

                bluf = str(result.get("bluf") or default_bluf)
                executive_summary = str(
                    result.get("executive_summary") or default_summary
                )

                if isinstance(result.get("implications"), list):
                    implications = [
                        str(item) for item in result["implications"]
                    ]

                if isinstance(result.get("recommendations"), list):
                    recommendations = [
                        str(item) for item in result["recommendations"]
                    ]

                if isinstance(result.get("intelligence_gaps"), list):
                    intelligence_gaps = [
                        str(item) for item in result["intelligence_gaps"]
                    ]

            except Exception:
                pass

        # Deterministic directional guardrail.
        #
        # Narrative generation may not infer a regional trajectory when
        # the underlying evidence contains no improving or deteriorating
        # directional support. This enforcement happens after model
        # generation so it cannot be overridden by the LLM.
        directional_values = {
            str(signal.direction or "").strip().lower()
            for signal in signals
        }

        has_deteriorating_support = (
            "deteriorating" in directional_values
        )
        has_improving_support = (
            "improving" in directional_values
        )

        if (
            not has_deteriorating_support
            and not has_improving_support
        ):
            risk_label = self.risk_level(risk_score)

            if len(signals) == 1:
                bluf = (
                    f"Political stability risk is assessed as "
                    f"{risk_label.lower()} at {risk_score:.1f}/100. "
                    "The available evidence is sparse and stable, and "
                    "does not support a broader regional directional trend."
                )
            else:
                bluf = (
                    f"Political stability risk is assessed as "
                    f"{risk_label.lower()} at {risk_score:.1f}/100. "
                    "Available evidence does not support a clear "
                    "improving or deteriorating regional trend."
                )

        return AgentAssessment(
            agent_key=self.agent_key,
            title="Political Stability Assessment",
            bluf=bluf,
            executive_summary=executive_summary,
            risk_score=risk_score,
            risk_level=self.risk_level(risk_score),
            confidence=confidence,
            analytical_status=self.analytical_status(risk_score),
            key_drivers=key_drivers,
            indicators=indicators,
            forecast_probabilities={
                "7d": probability_7d,
                "30d": probability_30d,
                "90d": probability_90d,
                "180d": probability_180d,
            },
            implications=implications,
            recommendations=recommendations,
            intelligence_gaps=intelligence_gaps,
            related_signal_ids=[
                signal.signal_id for signal in priority_signals
            ],
            country_iso3=(
                priority_signals[0].country_iso3
                if priority_signals
                else context.get("country_iso3")
            ),
            country_name=(
                priority_signals[0].country_name
                if priority_signals
                else context.get("country_name")
            ),
            region=(
                priority_signals[0].region
                if priority_signals
                else context.get("region")
            ),
        )
