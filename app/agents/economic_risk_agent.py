from __future__ import annotations

from typing import Any

from app.agents.base_agent import (
    AgentAssessment,
    AgentSignal,
    BaseStrategicAgent,
)
from app.services.strategic_agents.live_economic_collector import (
    collect_live_economic_signals,
)
from app.services.strategic_agents.nemotron_client import (
    nemotron_configured,
    run_nemotron_analysis,
)


class EconomicRiskAgent(BaseStrategicAgent):
    agent_key = "economic_risk"
    domain = "economic"

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
                        or f"economic-manual-{index}"
                    ),
                    domain="economic",
                    signal_type=str(
                        item.get("signal_type") or "economic_event"
                    ),
                    headline=str(
                        item.get("headline")
                        or "Untitled economic signal"
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
        country_iso3 = context.get("country_iso3")

        if not country_name or not country_iso3:
            return []

        return await collect_live_economic_signals(
            country_name=country_name,
            country_iso3=country_iso3,
            region=context.get("region"),
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
                title="Economic Risk Assessment",
                bluf="Insufficient current economic data for assessment.",
                executive_summary=(
                    "No usable macroeconomic or financial-risk signals "
                    "were available."
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
                implications=["Maintain routine monitoring."],
                recommendations=[
                    "Refresh macroeconomic data sources."
                ],
                intelligence_gaps=[
                    "Insufficient structured economic data."
                ],
                related_signal_ids=[],
                country_iso3=context.get("country_iso3"),
                country_name=context.get("country_name"),
                region=context.get("region"),
            )

        severity_scores = [
            signal.severity
            for signal in signals
        ]

        deteriorating = sum(
            1 for signal in signals
            if signal.direction == "deteriorating"
        )
        improving = sum(
            1 for signal in signals
            if signal.direction == "improving"
        )
        neutral = sum(
            1 for signal in signals
            if signal.direction == "neutral"
        )

        top_severity = sorted(
            severity_scores,
            reverse=True,
        )[:10]

        base_risk = (
            sum(top_severity)
            / len(top_severity)
        )

        trend_adjustment = (
            min(15, deteriorating * 3.0)
            - min(15, improving * 2.5)
        )

        risk_score = self.clamp_score(
            base_risk + trend_adjustment
        )

        confidence = self.clamp_score(
            sum(signal.confidence for signal in signals)
            / len(signals)
        )

        risk_signals = [
            signal
            for signal in signals
            if signal.signal_type != "gdp_current_usd"
        ]

        priority = sorted(
            risk_signals or signals,
            key=lambda item: (
                item.materiality_score,
                item.severity,
            ),
            reverse=True,
        )[:6]

        key_drivers = [
            {
                "headline": signal.headline,
                "severity": signal.severity,
                "confidence": signal.confidence,
                "source_key": signal.source_key,
                "direction": signal.direction,
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
                "30d": self.clamp_score(risk_score + 2),
                "90d": self.clamp_score(risk_score + 5),
                "180d": self.clamp_score(risk_score + 8),
            }
        elif net_direction < 0:
            forecasts = {
                "30d": self.clamp_score(risk_score - 2),
                "90d": self.clamp_score(risk_score - 5),
                "180d": self.clamp_score(risk_score - 8),
            }
        else:
            forecasts = {
                "30d": self.clamp_score(risk_score),
                "90d": self.clamp_score(risk_score + 1),
                "180d": self.clamp_score(risk_score + 2),
            }

        bluf = (
            f"Economic risk is assessed as "
            f"{self.risk_level(risk_score).lower()} at "
            f"{risk_score:.0f}/100."
        )
        summary = (
            f"The agent evaluated {len(signals)} macroeconomic and "
            f"financial signals."
        )
        implications = [
            "Economic stress may affect fiscal and market stability."
        ]
        recommendations = [
            "Monitor inflation, growth, reserves, and external balances."
        ]
        gaps = [
            "Debt and high-frequency market data may be incomplete."
        ]

        if nemotron_configured():
            try:
                evidence = [
                    {
                        "headline": signal.headline,
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
                        "You are a senior sovereign economic-risk analyst. "
                        "Use only supplied evidence. World Bank observations "
                        "are annual structural macroeconomic indicators, not "
                        "high-frequency or real-time signals. Clearly distinguish "
                        "structural indicators from any current news or market "
                        "signals. Do not recalculate the deterministic score. "
                        "Do not claim debt distress, default, currency crisis, "
                        "or banking crisis without direct evidence. "
                        "Return valid JSON only."
                    ),
                    user_prompt=(
                        f"Risk score: {risk_score}\n"
                        f"Risk level: {self.risk_level(risk_score)}\n"
                        f"Confidence: {confidence}\n"
                        f"Forecasts: {forecasts}\n"
                        f"Evidence: {evidence}\n\n"
                        "Return exactly:\n"
                        "{\n"
                        '  "bluf": "one sentence",\n'
                        '  "executive_summary": "one paragraph",\n'
                        '  "implications": ["one", "two"],\n'
                        '  "recommendations": ["one", "two"],\n'
                        '  "intelligence_gaps": ["one"]\n'
                        "}"
                    ),
                    max_tokens=1200,
                )

                bluf = str(result.get("bluf") or bluf)
                summary = str(
                    result.get("executive_summary") or summary
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
            title="Economic Risk Assessment",
            bluf=bluf,
            executive_summary=summary,
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
                signal.signal_id for signal in priority
            ],
            country_iso3=first.country_iso3,
            country_name=first.country_name,
            region=first.region,
        )
