from __future__ import annotations

from typing import Any

from app.agents.base_agent import (
    AgentAssessment,
    AgentSignal,
    BaseStrategicAgent,
)

from app.services.strategic_agents.nemotron_client import (
    nemotron_configured,
    run_nemotron_analysis,
)

from app.services.strategic_agents.live_conflict_collector import (
    collect_live_conflict_signals,
)


class ConflictMonitoringAgent(BaseStrategicAgent):
    agent_key = "conflict_monitoring"
    domain = "conflict"

    async def collect_signals(
        self,
        context: dict[str, Any],
    ) -> list[AgentSignal]:
        supplied_signals = context.get("signals", [])

        if not supplied_signals:
            return await collect_live_conflict_signals(
                country_name=context.get("country_name"),
                country_iso3=context.get("country_iso3"),
                region=context.get("region"),
                limit=int(context.get("signal_limit", 25)),
            )

        normalized: list[AgentSignal] = []

        for index, item in enumerate(supplied_signals):
            normalized.append(
                AgentSignal(
                    signal_id=str(
                        item.get("signal_id")
                        or item.get("id")
                        or f"manual-{index}"
                    ),
                    domain="conflict",
                    signal_type=str(
                        item.get("signal_type", "conflict_event")
                    ),
                    headline=str(
                        item.get("headline", "Untitled conflict signal")
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
                    direction=str(
                        item.get("direction", "neutral")
                    ),
                    event_time=item.get("event_time"),
                    source_key=item.get("source_key"),
                    evidence_url=item.get("evidence_url"),
                    entities=item.get("entities", []),
                    indicators=item.get("indicators", []),
                    tags=item.get("tags", []),
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
                title="Conflict Monitoring Assessment",
                bluf=(
                    "No material conflict signals were available for "
                    "the current assessment cycle."
                ),
                executive_summary=(
                    "The agent completed successfully but did not receive "
                    "sufficient current evidence to identify an elevated "
                    "conflict-development pattern."
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
                },
                implications=[
                    "Continue routine monitoring.",
                ],
                recommendations=[
                    "Refresh conflict and early-warning sources.",
                ],
                intelligence_gaps=[
                    "No current normalized conflict signals were available.",
                ],
                related_signal_ids=[],
            )

        weighted_scores: list[float] = []

        for signal in signals:
            weighted_score = (
                signal.severity * 0.45
                + signal.relevance * 0.20
                + signal.confidence * 0.20
                + signal.source_reliability * 0.15
            )
            weighted_scores.append(weighted_score)

        weighted_scores.sort(reverse=True)

        strongest_scores = weighted_scores[:10]
        base_score = sum(strongest_scores) / len(strongest_scores)

        deteriorating_count = sum(
            1
            for signal in signals
            if signal.direction == "deteriorating"
        )

        deterioration_adjustment = min(
            12,
            deteriorating_count * 2,
        )

        risk_score = self.clamp_score(
            base_score + deterioration_adjustment
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

        probability_7d = self.clamp_score(risk_score * 0.82)
        probability_30d = self.clamp_score(risk_score * 0.95)
        probability_90d = self.clamp_score(risk_score + 5)

        default_bluf = (
            f"Conflict risk is assessed as "
            f"{self.risk_level(risk_score).lower()} with a score "
            f"of {risk_score:.0f}/100."
        )
        default_summary = (
            f"The agent evaluated {len(signals)} conflict-related "
            f"signals. The assessment is primarily driven by the "
            f"highest-severity and most credible developments."
        )
        default_implications = [
            "Elevated conflict conditions may affect regional stability.",
            "Military, political, and commercial exposure should be reviewed.",
        ]
        default_recommendations = [
            "Continue monitoring the highest-materiality signals.",
            "Cross-check changes against Country Intelligence and Early Warning.",
        ]
        default_gaps = [
            "Some events may lack independent source corroboration.",
        ]

        bluf = default_bluf
        executive_summary = default_summary
        implications = default_implications
        recommendations = default_recommendations
        intelligence_gaps = default_gaps

        if nemotron_configured():
            try:
                signal_context = [
                    {
                        "headline": signal.headline,
                        "summary": signal.summary,
                        "country_iso3": signal.country_iso3,
                        "country_name": signal.country_name,
                        "region": signal.region,
                        "signal_type": signal.signal_type,
                        "severity": signal.severity,
                        "confidence": signal.confidence,
                        "direction": signal.direction,
                        "source_key": signal.source_key,
                    }
                    for signal in priority_signals
                ]

                nemotron_result = run_nemotron_analysis(
                    system_prompt=(
                        "You are a senior geopolitical intelligence analyst. "
                        "Use only the supplied evidence. Clearly distinguish "
                        "observed facts from analytical inference. Do not claim "
                        "blockade, invasion, mobilization, or operational intent "
                        "unless directly supported by the supplied signals. "
                        "Use calibrated estimative language such as may, could, "
                        "suggests, or is consistent with when evidence is incomplete. "
                        "Do not change or recalculate the deterministic risk score. "
                        "Return valid JSON only, without markdown."
                    ),
                    user_prompt=(
                        "Produce an analytical narrative for a conflict-risk "
                        "assessment.\n\n"
                        f"Deterministic risk score: {risk_score}\n"
                        f"Risk level: {self.risk_level(risk_score)}\n"
                        f"Confidence: {confidence}\n"
                        f"Forecast probabilities: 7d={probability_7d}, "
                        f"30d={probability_30d}, 90d={probability_90d}\n"
                        f"Signals: {signal_context}\n\n"
                        "Return exactly this JSON structure:\n"
                        "{\n"
                        '  "bluf": "one concise strategic judgment",\n'
                        '  "executive_summary": "one short analytical paragraph",\n'
                        '  "implications": ["implication one", "implication two"],\n'
                        '  "recommendations": ["recommendation one", "recommendation two"],\n'
                        '  "intelligence_gaps": ["gap one"]\n'
                        "}"
                    ),
                    max_tokens=1200,
                )

                bluf = str(nemotron_result.get("bluf") or default_bluf)
                executive_summary = str(
                    nemotron_result.get("executive_summary")
                    or default_summary
                )

                if isinstance(nemotron_result.get("implications"), list):
                    implications = [
                        str(item)
                        for item in nemotron_result["implications"]
                    ]

                if isinstance(nemotron_result.get("recommendations"), list):
                    recommendations = [
                        str(item)
                        for item in nemotron_result["recommendations"]
                    ]

                if isinstance(nemotron_result.get("intelligence_gaps"), list):
                    intelligence_gaps = [
                        str(item)
                        for item in nemotron_result["intelligence_gaps"]
                    ]

            except Exception:
                pass

        return AgentAssessment(
            agent_key=self.agent_key,
            title="Conflict Monitoring Assessment",
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
            },
            implications=implications,
            recommendations=recommendations,
            intelligence_gaps=intelligence_gaps,
            related_signal_ids=[
                signal.signal_id
                for signal in priority_signals
            ],
            country_iso3=(
                priority_signals[0].country_iso3
                if priority_signals
                else context.get("country_iso3")
            ),
            country_name=(
                priority_signals[0].country_name
                if priority_signals
                else None
            ),
            region=(
                priority_signals[0].region
                if priority_signals
                else context.get("region")
            ),
        )
