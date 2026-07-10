from __future__ import annotations

from typing import Any

from app.agents.base_agent import (
    AgentAssessment,
    AgentSignal,
    BaseStrategicAgent,
)
from app.services.strategic_agents.live_trade_sanctions_collector import (
    collect_live_trade_sanctions_signals,
)
from app.services.strategic_agents.nemotron_client import (
    nemotron_configured,
    run_nemotron_analysis,
)


class TradeSanctionsAgent(BaseStrategicAgent):
    agent_key = "trade_sanctions"
    domain = "trade_sanctions"

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
                        or f"trade-sanctions-manual-{index}"
                    ),
                    domain="trade_sanctions",
                    signal_type=str(
                        item.get("signal_type")
                        or "trade_sanctions_event"
                    ),
                    headline=str(
                        item.get("headline")
                        or "Untitled trade or sanctions signal"
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

        country_name = context.get("country_name")

        if not country_name:
            return []

        return await collect_live_trade_sanctions_signals(
            country_name=country_name,
            country_iso3=context.get("country_iso3"),
            region=context.get("region"),
            commodity=context.get("commodity"),
            sector=context.get("sector"),
            limit=int(context.get("signal_limit", 25)),
        )

    async def analyze(
        self,
        signals: list[AgentSignal],
        context: dict[str, Any],
    ) -> AgentAssessment:
        if not signals:
            return AgentAssessment(
                agent_key=self.agent_key,
                title="Trade and Sanctions Assessment",
                bluf=(
                    "No material trade-restriction or sanctions evidence "
                    "was available for the current cycle."
                ),
                executive_summary=(
                    "The agent found no usable OFAC, export-control, tariff, "
                    "embargo, or trade-restriction signals."
                ),
                risk_score=0,
                risk_level="Low",
                confidence=20,
                analytical_status="nominal",
                key_drivers=[],
                indicators=[],
                forecast_probabilities={
                    "30d": 10,
                    "90d": 15,
                    "180d": 20,
                },
                implications=["Continue routine monitoring."],
                recommendations=[
                    "Refresh sanctions and trade-restriction sources."
                ],
                intelligence_gaps=[
                    "No current normalized trade or sanctions evidence."
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

        structural = [
            signal
            for signal in priority
            if signal.signal_type == "country_sanctions_exposure"
        ]

        event_signals = [
            signal
            for signal in priority
            if signal.signal_type != "country_sanctions_exposure"
        ]

        structural_baseline = (
            max(signal.severity for signal in structural)
            if structural
            else 0.0
        )

        event_modifier = 0.0

        for signal in event_signals:
            if signal.direction == "deteriorating":
                event_modifier += max(
                    0.0,
                    signal.severity - 35.0,
                ) * 0.18
            elif signal.direction == "improving":
                event_modifier -= max(
                    0.0,
                    signal.severity - 30.0,
                ) * 0.12
            else:
                event_modifier += max(
                    0.0,
                    signal.severity - 55.0,
                ) * 0.08

        if not structural and event_signals:
            structural_baseline = max(
                signal.severity
                for signal in event_signals
            ) * 0.75

        risk_score = self.clamp_score(
            structural_baseline + event_modifier
        )

        confidence = self.clamp_score(
            sum(signal.confidence for signal in priority)
            / len(priority)
        )

        deteriorating = sum(
            1
            for signal in event_signals
            if signal.direction == "deteriorating"
        )
        improving = sum(
            1
            for signal in event_signals
            if signal.direction == "improving"
        )

        net_direction = deteriorating - improving

        if net_direction > 0:
            forecasts = {
                "30d": self.clamp_score(risk_score + 2),
                "90d": self.clamp_score(risk_score + 5),
                "180d": self.clamp_score(risk_score + 7),
            }
        elif net_direction < 0:
            forecasts = {
                "30d": self.clamp_score(risk_score - 2),
                "90d": self.clamp_score(risk_score - 4),
                "180d": self.clamp_score(risk_score - 6),
            }
        else:
            forecasts = {
                "30d": risk_score,
                "90d": risk_score,
                "180d": risk_score,
            }

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

        bluf = (
            f"Trade and sanctions risk is assessed as "
            f"{self.risk_level(risk_score).lower()} at "
            f"{risk_score:.0f}/100."
        )
        executive_summary = (
            f"The agent evaluated {len(signals)} sanctions, tariff, "
            f"export-control, and trade-restriction signals."
        )
        implications = [
            "Sanctions exposure may constrain payments, financing, and trade execution.",
            "Export controls and tariffs may affect strategic sectors and supply chains.",
        ]
        recommendations = [
            "Screen counterparties, beneficial owners, and transactions against current sanctions lists and applicable ownership rules.",
            "Escalate material matches for qualified sanctions-compliance or legal review, including licenses and exemptions.",
        ]
        gaps = [
            "UN Comtrade trade-flow data is not configured.",
            "Ownership and control relationships may not be fully resolved.",
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
                        "You are a senior sanctions, trade-control, and "
                        "geoeconomic-risk analyst. Use only supplied evidence. "
                        "Distinguish existing structural sanctions exposure from "
                        "newly imposed measures. An OFAC match does not by itself "
                        "prove a new designation, sanctions violation, blocked "
                        "transaction, beneficial ownership relationship, or automatic "
                        "secondary-sanctions exposure. Do not state that every "
                        "Iran-related transaction or engagement is prohibited. "
                        "Explain that restrictions depend on the parties, ownership, "
                        "applicable sanctions authority, jurisdiction, transaction "
                        "facts, licenses, exemptions, and authorizations. Do not say "
                        "that all non-U.S. persons automatically face secondary "
                        "sanctions. Describe matches as screening or exposure indicators, "
                        "not final legal determinations. Do not infer active procurement "
                        "channels, tariff rates, trade volumes, revenue losses, or "
                        "supply-chain effects unless explicitly supplied. Recommend "
                        "qualified sanctions-compliance or legal review for material "
                        "matches. Do not recalculate the deterministic score. "
                        "Return valid JSON only."
                    ),
                    user_prompt=(
                        f"Risk score: {risk_score}\n"
                        f"Risk level: {self.risk_level(risk_score)}\n"
                        f"Confidence: {confidence}\n"
                        f"Projected risk scores: {forecasts}\n"
                        f"Evidence: {evidence}\n\n"
                        "Return exactly:\n"
                        "{\n"
                        '  "bluf": "one concise strategic judgment",\n'
                        '  "executive_summary": "one short paragraph",\n'
                        '  "implications": ["one", "two"],\n'
                        '  "recommendations": ["one", "two"],\n'
                        '  "intelligence_gaps": ["one", "two"]\n'
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
            title="Trade and Sanctions Assessment",
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
