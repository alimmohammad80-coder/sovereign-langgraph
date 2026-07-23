from __future__ import annotations

from typing import Any

from app.agents.base_agent import (
    AgentAssessment,
    AgentSignal,
    BaseStrategicAgent,
)
from app.services.strategic_agents.live_energy_collector import (
    collect_live_energy_signals,
)
from app.services.strategic_agents.regional_energy_baselines import (
    collect_regional_energy_baselines,
)
from app.services.strategic_agents.nemotron_client import (
    nemotron_configured,
    run_nemotron_analysis,
)


class EnergySecurityAgent(BaseStrategicAgent):
    agent_key = "energy_security"
    domain = "energy"

    async def collect_signals(
        self,
        context: dict[str, Any],
    ) -> list[AgentSignal]:
        supplied = context.get("signals", [])

        if supplied:
            return [
                AgentSignal(
                    signal_id=str(
                        item.get("signal_id")
                        or item.get("id")
                        or f"energy-manual-{index}"
                    ),
                    domain="energy",
                    signal_type=str(
                        item.get("signal_type")
                        or "energy_security_event"
                    ),
                    headline=str(
                        item.get("headline")
                        or "Untitled energy signal"
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
                    indicators=item.get("indicators", []),
                )
                for index, item in enumerate(supplied)
            ]

        live_signals = await collect_live_energy_signals(
            country_name=context.get("country_name"),
            country_iso3=context.get("country_iso3"),
            region=context.get("region"),
            limit=int(context.get("signal_limit", 25)),
        )

        regional_baselines = collect_regional_energy_baselines(
            context.get("region")
        )

        combined = [
            *live_signals,
            *regional_baselines,
        ]

        deduplicated: dict[str, AgentSignal] = {}

        for signal in combined:
            current = deduplicated.get(signal.signal_id)

            if (
                current is None
                or signal.materiality_score
                > current.materiality_score
            ):
                deduplicated[signal.signal_id] = signal

        return sorted(
            deduplicated.values(),
            key=lambda item: (
                item.materiality_score,
                item.severity,
                item.confidence,
            ),
            reverse=True,
        )[: int(context.get("signal_limit", 25))]

    async def analyze(
        self,
        signals: list[AgentSignal],
        context: dict[str, Any],
    ) -> AgentAssessment:
        if not signals:
            return AgentAssessment(
                agent_key=self.agent_key,
                title="Energy Security Assessment",
                bluf="Insufficient current energy-security evidence.",
                executive_summary=(
                    "The agent found no usable energy infrastructure, "
                    "market, weather, chokepoint, or sanctions signals."
                ),
                risk_score=0,
                risk_level="Low",
                confidence=20,
                analytical_status="nominal",
                key_drivers=[],
                indicators=[],
                forecast_probabilities={
                    "7d": 5,
                    "30d": 10,
                    "90d": 15,
                },
                implications=["Continue routine energy monitoring."],
                recommendations=[
                    "Refresh energy and maritime data sources."
                ],
                intelligence_gaps=[
                    "No current normalized energy signals were available."
                ],
                related_signal_ids=[],
                country_iso3=context.get("country_iso3"),
                country_name=context.get("country_name"),
                region=context.get("region"),
            )

        priority = sorted(
            signals,
            key=lambda item: (
                item.materiality_score,
                item.severity,
                item.confidence,
            ),
            reverse=True,
        )[:8]

        risk_signals = [
            signal
            for signal in priority
            if signal.signal_type != "energy_market_signal"
        ]

        scoring_signals = risk_signals or priority

        structural_signals = [
            signal
            for signal in scoring_signals
            if signal.signal_type == "energy_chokepoint_risk"
        ]

        disruption_signals = [
            signal
            for signal in scoring_signals
            if signal.signal_type in {
                "energy_infrastructure_disruption",
                "energy_supply_disruption",
                "pipeline_outage",
                "terminal_outage",
                "energy_sanctions_exposure",
            }
        ]

        weather_signals = [
            signal
            for signal in scoring_signals
            if signal.signal_type == "marine_weather_disruption"
        ]

        other_risk_signals = [
            signal
            for signal in scoring_signals
            if signal.signal_type not in {
                "energy_chokepoint_risk",
                "energy_market_signal",
                "marine_weather_disruption",
                "energy_infrastructure_disruption",
                "energy_supply_disruption",
                "pipeline_outage",
                "terminal_outage",
                "energy_sanctions_exposure",
            }
        ]

        if structural_signals:
            structural_baseline = max(
                signal.severity
                for signal in structural_signals
            )
        elif scoring_signals:
            structural_baseline = max(
                signal.severity
                for signal in scoring_signals
            )
        else:
            structural_baseline = 0.0

        disruption_modifier = 0.0

        for signal in disruption_signals:
            disruption_modifier += max(
                0.0,
                signal.severity - 40.0,
            ) * 0.15

        weather_modifier = 0.0

        for signal in weather_signals:
            # Benign weather does not reduce structural exposure.
            # Only materially adverse weather adds operational risk.
            if signal.severity >= 50:
                weather_modifier += (
                    signal.severity - 40.0
                ) * 0.10

        other_modifier = 0.0

        for signal in other_risk_signals:
            if signal.direction == "deteriorating":
                other_modifier += max(
                    0.0,
                    signal.severity - 40.0,
                ) * 0.10

        deteriorating = sum(
            1
            for signal in priority
            if signal.direction == "deteriorating"
        )
        improving = sum(
            1
            for signal in priority
            if signal.direction == "improving"
        )

        directional_modifier = (
            min(8.0, deteriorating * 2.0)
            - min(6.0, improving * 1.5)
        )

        risk_score = self.clamp_score(
            structural_baseline
            + disruption_modifier
            + weather_modifier
            + other_modifier
            + directional_modifier
        )

        confidence = self.clamp_score(
            sum(signal.confidence for signal in priority)
            / len(priority)
        )

        key_drivers = [
            {
                "headline": signal.headline,
                "severity": signal.severity,
                "confidence": signal.confidence,
                "source_key": signal.source_key,
                "direction": signal.direction,
                "signal_type": signal.signal_type,
            }
            for signal in priority
        ]

        indicators = [
            {
                "name": signal.signal_type,
                "value": signal.severity,
                "direction": signal.direction,
            }
            for signal in priority
        ]

        net_direction = deteriorating - improving

        if net_direction > 0:
            forecasts = {
                "7d": self.clamp_score(risk_score),
                "30d": self.clamp_score(risk_score + 3),
                "90d": self.clamp_score(risk_score + 6),
            }
        elif net_direction < 0:
            forecasts = {
                "7d": self.clamp_score(risk_score - 2),
                "30d": self.clamp_score(risk_score - 4),
                "90d": self.clamp_score(risk_score - 6),
            }
        else:
            forecasts = {
                "7d": self.clamp_score(risk_score),
                "30d": self.clamp_score(risk_score),
                "90d": self.clamp_score(risk_score),
            }

        bluf = (
            f"Energy security risk is assessed as "
            f"{self.risk_level(risk_score).lower()} at "
            f"{risk_score:.0f}/100."
        )
        executive_summary = (
            f"The agent evaluated {len(signals)} energy-security signals "
            f"covering chokepoints, markets, sanctions, and marine weather."
        )
        implications = [
            "Energy transit disruption could increase transport and commodity costs.",
            "Concentrated chokepoint exposure may amplify regional disruption.",
        ]
        recommendations = [
            "Monitor priority chokepoints and energy-shipping routes.",
            "Track oil, LNG, tanker, sanctions, and infrastructure signals.",
        ]
        gaps = [
            "Pipeline outages, storage levels, and import dependency may be incomplete."
        ]

        if nemotron_configured():
            try:
                evidence = [
                    {
                        "headline": signal.headline,
                        "summary": signal.summary,
                        "signal_type": signal.signal_type,
                        "severity": signal.severity,
                        "confidence": signal.confidence,
                        "direction": signal.direction,
                        "source": signal.source_key,
                        "indicators": signal.indicators,
                    }
                    for signal in priority
                ]

                result = run_nemotron_analysis(
                    system_prompt=(
                        "You are a senior energy-security and geopolitical-risk "
                        "analyst. Use only supplied evidence. Distinguish "
                        "structural chokepoint exposure from confirmed current "
                        "disruptions. Do not claim closure, blockade, supply loss, "
                        "pipeline outage, attack, or price shock unless directly "
                        "supported. Marine weather and EIA observations are "
                        "operational context, not proof of disruption. Do not infer "
                        "zero spare capacity, exact rerouting capacity, production "
                        "losses, or price effects unless those figures are explicitly "
                        "provided. Use the phrase limited rerouting capacity only when "
                        "that wording is present in the evidence. Do not convert a traffic "
                        "percentage into a share of global oil, LNG, or energy flows unless "
                        "the supplied evidence explicitly defines that percentage. Do not "
                        "recalculate the deterministic score. Return valid JSON only."
                    ),
                    user_prompt=(
                        f"Risk score: {risk_score}\n"
                        f"Risk level: {self.risk_level(risk_score)}\n"
                        f"Confidence: {confidence}\n"
                        f"Forecasts: {forecasts}\n"
                        f"Evidence: {evidence}\n\n"
                        "Return exactly:\n"
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

                bluf = str(result.get("bluf") or bluf)
                executive_summary = str(
                    result.get("executive_summary")
                    or executive_summary
                )

                if isinstance(result.get("implications"), list):
                    implications = [
                        str(item)
                        for item in result["implications"]
                    ]

                if isinstance(result.get("recommendations"), list):
                    recommendations = [
                        str(item)
                        for item in result["recommendations"]
                    ]

                if isinstance(result.get("intelligence_gaps"), list):
                    gaps = [
                        str(item)
                        for item in result["intelligence_gaps"]
                    ]
            except Exception:
                pass

        first = priority[0]

        return AgentAssessment(
            agent_key=self.agent_key,
            title="Energy Security Assessment",
            bluf=bluf,
            executive_summary=executive_summary,
            risk_score=risk_score,
            risk_level=self.risk_level(risk_score),
            confidence=confidence,
            analytical_status=self.analytical_status(risk_score),
            key_drivers=key_drivers,
            indicators=indicators,
            forecast_probabilities=forecasts,
            implications=implications,
            recommendations=recommendations,
            intelligence_gaps=gaps,
            related_signal_ids=[
                signal.signal_id
                for signal in priority
            ],
            country_iso3=(
                first.country_iso3
                or context.get("country_iso3")
            ),
            country_name=(
                first.country_name
                or context.get("country_name")
            ),
            region=(
                first.region
                or context.get("region")
            ),
        )
