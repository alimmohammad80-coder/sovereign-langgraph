from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import (
    AgentAssessment,
    AgentSignal,
    BaseStrategicAgent,
)
from app.intelligence.storage import get_supabase_client
from app.services.strategic_agents.nemotron_client import (
    nemotron_configured,
    run_nemotron_analysis,
)


DOMAIN_AGENT_KEYS = (
    "conflict_monitoring",
    "political_stability",
    "economic_risk",
    "energy_security",
    "trade_sanctions",
)


DOMAIN_LABELS = {
    "conflict_monitoring": "Conflict Monitoring",
    "political_stability": "Political Stability",
    "economic_risk": "Economic Risk",
    "energy_security": "Energy Security",
    "trade_sanctions": "Trade and Sanctions",
}


class ExecutiveBriefingAgent(BaseStrategicAgent):
    agent_key = "executive_briefing"
    domain = "cross_domain"
    scoring_version = "executive-briefing-v1"

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _age_hours(cls, value: str | None) -> float | None:
        parsed = cls._parse_datetime(value)

        if parsed is None:
            return None

        return max(
            0.0,
            (
                datetime.now(timezone.utc) - parsed
            ).total_seconds() / 3600,
        )

    @staticmethod
    def _row_matches_scope(
        row: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        requested_iso3 = str(
            context.get("country_iso3") or ""
        ).strip().upper()

        requested_country = str(
            context.get("country_name") or ""
        ).strip().lower()

        requested_region = str(
            context.get("region") or ""
        ).strip().lower()

        row_iso3 = str(
            row.get("country_iso3") or ""
        ).strip().upper()

        row_country = str(
            row.get("country_name") or ""
        ).strip().lower()

        row_region = str(
            row.get("region") or ""
        ).strip().lower()

        if requested_iso3 and row_iso3:
            return requested_iso3 == row_iso3

        if requested_country and row_country:
            return requested_country == row_country

        if requested_region and row_region:
            return requested_region == row_region

        return not (
            requested_iso3
            or requested_country
            or requested_region
        )

    def _load_latest_output(
        self,
        agent_key: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        client = get_supabase_client()

        if client is None:
            raise RuntimeError(
                "Supabase client is not configured."
            )

        result = (
            client.table("strategic_agent_outputs")
            .select("*")
            .eq("agent_key", agent_key)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )

        rows = result.data or []

        for row in rows:
            if self._row_matches_scope(row, context):
                return row

        return None

    async def collect_signals(
        self,
        context: dict[str, Any],
    ) -> list[AgentSignal]:
        signals: list[AgentSignal] = []

        freshness_hours = float(
            context.get(
                "freshness_threshold_hours",
                168,
            )
        )

        for agent_key in DOMAIN_AGENT_KEYS:
            row = self._load_latest_output(
                agent_key,
                context,
            )

            if row is None:
                continue

            created_at = (
                row.get("created_at")
                or row.get("valid_from")
            )

            age_hours = self._age_hours(created_at)

            if age_hours is None:
                freshness_status = "unknown"
                freshness_factor = 0.65
            elif age_hours <= freshness_hours:
                freshness_status = "current"
                freshness_factor = 1.0
            elif age_hours <= freshness_hours * 2:
                freshness_status = "stale"
                freshness_factor = 0.70
            else:
                freshness_status = "expired"
                freshness_factor = 0.40

            risk_score = float(
                row.get("risk_score") or 0
            )
            confidence = float(
                row.get("confidence") or 0
            )

            adjusted_confidence = self.clamp_score(
                confidence * freshness_factor
            )

            materiality = self.clamp_score(
                risk_score * 0.65
                + adjusted_confidence * 0.25
                + freshness_factor * 10
            )

            payload = (
                row.get("presentation_payload")
                if isinstance(
                    row.get("presentation_payload"),
                    dict,
                )
                else {}
            )

            key_drivers = (
                row.get("key_drivers")
                or payload.get("key_drivers")
                or []
            )

            forecasts = (
                row.get("forecast_probabilities")
                or payload.get("forecast_probabilities")
                or {}
            )

            insufficient_evidence = (
                risk_score == 0
                and confidence <= 30
                and not key_drivers
            )

            inferred_direction = (
                "unknown"
                if insufficient_evidence
                else self._infer_direction(
                    forecasts,
                    risk_score,
                )
            )

            signals.append(
                AgentSignal(
                    signal_id=(
                        f"executive-source-"
                        f"{agent_key}-"
                        f"{row.get('id') or row.get('run_id')}"
                    ),
                    domain="cross_domain",
                    signal_type="domain_agent_assessment",
                    headline=(
                        f"{DOMAIN_LABELS[agent_key]}: "
                        f"{row.get('risk_level') or 'Unknown'} "
                        f"({risk_score:.1f})"
                    ),
                    summary=(
                        str(row.get("bluf") or "")
                    ),
                    country_iso3=row.get(
                        "country_iso3"
                    ),
                    country_name=row.get(
                        "country_name"
                    ),
                    region=row.get("region"),
                    severity=risk_score,
                    relevance=100,
                    confidence=adjusted_confidence,
                    source_reliability=95,
                    materiality_score=materiality,
                    direction=inferred_direction,
                    event_time=created_at,
                    source_key=agent_key,
                    indicators=[
                        {
                            "name": "domain_risk_score",
                            "value": risk_score,
                        },
                        {
                            "name": "domain_confidence",
                            "value": confidence,
                        },
                        {
                            "name": "freshness_status",
                            "value": freshness_status,
                        },
                        {
                            "name": "age_hours",
                            "value": (
                                round(age_hours, 2)
                                if age_hours is not None
                                else None
                            ),
                        },
                        {
                            "name": "domain_key_drivers",
                            "value": key_drivers[:3],
                        },
                        {
                            "name": "domain_forecasts",
                            "value": forecasts,
                        },
                    ],
                    tags=[
                        agent_key,
                        freshness_status,
                    ],
                )
            )

        return signals

    @staticmethod
    def _infer_direction(
        forecasts: dict[str, Any],
        current_score: float,
    ) -> str:
        numeric_values = []

        for value in forecasts.values():
            try:
                numeric_values.append(float(value))
            except (TypeError, ValueError):
                continue

        if not numeric_values:
            return "neutral"

        terminal = numeric_values[-1]

        if terminal >= current_score + 3:
            return "deteriorating"

        if terminal <= current_score - 3:
            return "improving"

        return "neutral"

    async def analyze(
        self,
        signals: list[AgentSignal],
        context: dict[str, Any],
    ) -> AgentAssessment:
        expected_count = len(DOMAIN_AGENT_KEYS)
        available_count = len(signals)

        missing_agents = [
            DOMAIN_LABELS[key]
            for key in DOMAIN_AGENT_KEYS
            if key not in {
                signal.source_key
                for signal in signals
            }
        ]

        if not signals:
            return AgentAssessment(
                agent_key=self.agent_key,
                title="Executive Intelligence Briefing",
                bluf=(
                    "No current domain-agent outputs were available "
                    "for executive synthesis."
                ),
                executive_summary=(
                    "The briefing could not be generated because no "
                    "matching stored assessments were found."
                ),
                risk_score=0,
                risk_level="Low",
                confidence=10,
                analytical_status="nominal",
                key_drivers=[],
                indicators=[],
                forecast_probabilities={
                    "7d": 0,
                    "30d": 0,
                    "90d": 0,
                    "180d": 0,
                },
                implications=[
                    "Executive situational awareness is incomplete."
                ],
                recommendations=[
                    "Run the domain agents for the selected scope."
                ],
                intelligence_gaps=[
                    "All five domain assessments are missing."
                ],
                related_signal_ids=[],
                country_iso3=context.get("country_iso3"),
                country_name=context.get("country_name"),
                region=context.get("region"),
            )

        ranked = sorted(
            signals,
            key=lambda signal: (
                signal.materiality_score,
                signal.severity,
                signal.confidence,
            ),
            reverse=True,
        )

        scores = [
            signal.severity
            for signal in ranked
        ]

        highest_score = max(scores)

        elevated_count = sum(
            1
            for score in scores
            if score >= 50
        )

        high_count = sum(
            1
            for score in scores
            if score >= 70
        )

        deteriorating_count = sum(
            1
            for signal in ranked
            if signal.direction == "deteriorating"
            and "insufficient_evidence" not in signal.tags
        )

        stale_count = sum(
            1
            for signal in ranked
            if "stale" in signal.tags
            or "expired" in signal.tags
        )

        assessed_signals = [
            signal
            for signal in ranked
            if "insufficient_evidence" not in signal.tags
        ]

        supporting_scores = sorted(
            (
                signal.severity
                for signal in assessed_signals
                if signal.severity < highest_score
            ),
            reverse=True,
        )[:3]

        # Cross-domain reinforcement is deliberately bounded.
        # Supporting risks strengthen the executive priority judgment
        # without being stacked as independent additive probabilities.
        reinforcement_bonus = min(
            5.0,
            sum(
                max(0.0, score - 50.0) * 0.035
                for score in supporting_scores
            ),
        )

        deterioration_bonus = min(
            3.0,
            sum(
                1.0
                for signal in assessed_signals
                if signal.direction == "deteriorating"
            ),
        )

        completeness_penalty = (
            expected_count - available_count
        ) * 3.0

        stale_penalty = stale_count * 2.0

        # Missing or stale domain coverage reduces confidence,
        # not the underlying strategic risk represented by available evidence.
        executive_score = self.clamp_score(
            highest_score
            + reinforcement_bonus
            + deterioration_bonus
        )

        average_confidence = (
            sum(
                signal.confidence
                for signal in ranked
            )
            / len(ranked)
        )

        coverage_factor = (
            available_count / expected_count
        )

        confidence = self.clamp_score(
            average_confidence
            * coverage_factor
            - stale_count * 3
        )

        domain_dashboard = [
            {
                "agent_key": signal.source_key,
                "domain": DOMAIN_LABELS.get(
                    str(signal.source_key),
                    str(signal.source_key),
                ),
                "risk_score": signal.severity,
                "risk_level": self.risk_level(
                    signal.severity
                ),
                "confidence": signal.confidence,
                "direction": signal.direction,
                "freshness_status": (
                    signal.tags[1]
                    if len(signal.tags) > 1
                    else "unknown"
                ),
                "bluf": signal.summary,
            }
            for signal in ranked
        ]

        convergence_domains = [
            DOMAIN_LABELS.get(
                str(signal.source_key),
                str(signal.source_key),
            )
            for signal in ranked
            if signal.severity >= 50
            and "insufficient_evidence" not in signal.tags
        ]

        top_domains = [
            DOMAIN_LABELS.get(
                str(signal.source_key),
                str(signal.source_key),
            )
            for signal in ranked[:3]
        ]

        outlook = self._build_outlook(
            ranked,
            executive_score,
        )

        bluf = (
            f"Executive risk is assessed as "
            f"{self.risk_level(executive_score).lower()} "
            f"at {executive_score:.1f}/100, led by "
            f"{', '.join(top_domains)}."
        )

        executive_summary = (
            f"The briefing synthesized {available_count} of "
            f"{expected_count} domain-agent assessments. "
            f"{elevated_count} domains are Elevated or above, "
            f"with {deteriorating_count} showing a worsening trajectory."
        )

        implications = [
            (
                "Multiple elevated domains may reinforce one another, "
                "increasing the probability of compound strategic effects."
            ),
            (
                "High-risk domain findings should be reviewed together "
                "rather than managed as isolated issues."
            ),
        ]

        recommendations = [
            (
                "Prioritize executive review of the highest-risk domains "
                "and assign owners for monitoring and mitigation."
            ),
            (
                "Refresh stale or missing domain assessments before "
                "making major operational or investment decisions."
            ),
        ]

        intelligence_gaps = []

        if missing_agents:
            intelligence_gaps.append(
                "Missing domain outputs: "
                + ", ".join(missing_agents)
                + "."
            )

        if stale_count:
            intelligence_gaps.append(
                f"{stale_count} source assessment(s) are stale or expired."
            )

        if not intelligence_gaps:
            intelligence_gaps.append(
                "No major domain-coverage gap was identified."
            )

        key_drivers = [
            {
                "headline": signal.headline,
                "severity": signal.severity,
                "confidence": signal.confidence,
                "source_key": signal.source_key,
                "direction": signal.direction,
                "summary": signal.summary,
            }
            for signal in ranked
        ]

        indicators = [
            {
                "name": "domain_dashboard",
                "value": domain_dashboard,
            },
            {
                "name": "available_domain_count",
                "value": available_count,
            },
            {
                "name": "missing_domain_count",
                "value": (
                    expected_count - available_count
                ),
            },
            {
                "name": "elevated_domain_count",
                "value": elevated_count,
            },
            {
                "name": "high_domain_count",
                "value": high_count,
            },
            {
                "name": "deteriorating_domain_count",
                "value": deteriorating_count,
            },
            {
                "name": "convergence_domains",
                "value": convergence_domains,
            },
        ]

        if nemotron_configured():
            try:
                evidence = {
                    "executive_score": executive_score,
                    "executive_risk_level": self.risk_level(
                        executive_score
                    ),
                    "confidence": confidence,
                    "domain_dashboard": domain_dashboard,
                    "outlook": outlook,
                    "missing_domains": missing_agents,
                    "stale_domain_count": stale_count,
                }

                result = run_nemotron_analysis(
                    system_prompt=(
                        "You are a senior strategic intelligence briefing "
                        "officer. Synthesize only the supplied domain-agent "
                        "assessments. Preserve each domain's deterministic "
                        "score and do not invent facts, events, quantities, "
                        "probabilities, legal conclusions, or causal links. "
                        "Distinguish structural exposure from active events. "
                        "Identify genuine cross-domain convergence only when "
                        "supported by multiple supplied assessments. Do not "
                        "describe projected risk scores as calibrated event "
                        "probabilities. Return valid JSON only."
                    ),
                    user_prompt=(
                        f"Evidence: {evidence}\n\n"
                        "Return exactly:\n"
                        "{\n"
                        '  "bluf": "one concise executive judgment",\n'
                        '  "executive_summary": "one short paragraph",\n'
                        '  "implications": ["one", "two"],\n'
                        '  "recommendations": ["one", "two"],\n'
                        '  "intelligence_gaps": ["one", "two"]\n'
                        "}"
                    ),
                    max_tokens=1400,
                )

                bluf = str(
                    result.get("bluf")
                    or bluf
                )

                executive_summary = str(
                    result.get("executive_summary")
                    or executive_summary
                )

                if isinstance(
                    result.get("implications"),
                    list,
                ):
                    implications = [
                        str(item)
                        for item in result["implications"]
                    ]

                if isinstance(
                    result.get("recommendations"),
                    list,
                ):
                    recommendations = [
                        str(item)
                        for item in result["recommendations"]
                    ]

                if isinstance(
                    result.get("intelligence_gaps"),
                    list,
                ):
                    intelligence_gaps = [
                        str(item)
                        for item in result["intelligence_gaps"]
                    ]

            except Exception:
                pass

        return AgentAssessment(
            agent_key=self.agent_key,
            title="Executive Intelligence Briefing",
            bluf=bluf,
            executive_summary=executive_summary,
            risk_score=executive_score,
            risk_level=self.risk_level(
                executive_score
            ),
            confidence=confidence,
            analytical_status=self.analytical_status(
                executive_score
            ),
            key_drivers=key_drivers,
            indicators=indicators,
            forecast_probabilities=outlook,
            implications=implications,
            recommendations=recommendations,
            intelligence_gaps=intelligence_gaps,
            related_signal_ids=[
                signal.signal_id
                for signal in ranked
            ],
            country_iso3=context.get("country_iso3"),
            country_name=context.get("country_name"),
            region=context.get("region"),
        )

    def _build_outlook(
        self,
        signals: list[AgentSignal],
        executive_score: float,
    ) -> dict[str, float]:
        deteriorating = sum(
            1
            for signal in signals
            if signal.direction == "deteriorating"
        )

        improving = sum(
            1
            for signal in signals
            if signal.direction == "improving"
        )

        net_direction = deteriorating - improving

        if net_direction > 0:
            return {
                "7d": executive_score,
                "30d": self.clamp_score(
                    executive_score + 2
                ),
                "90d": self.clamp_score(
                    executive_score + 4
                ),
                "180d": self.clamp_score(
                    executive_score + 6
                ),
            }

        if net_direction < 0:
            return {
                "7d": executive_score,
                "30d": self.clamp_score(
                    executive_score - 2
                ),
                "90d": self.clamp_score(
                    executive_score - 4
                ),
                "180d": self.clamp_score(
                    executive_score - 5
                ),
            }

        return {
            "7d": executive_score,
            "30d": executive_score,
            "90d": executive_score,
            "180d": executive_score,
        }
