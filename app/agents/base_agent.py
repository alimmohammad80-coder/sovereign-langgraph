from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentSignal:
    signal_id: str
    domain: str
    signal_type: str
    headline: str

    summary: str | None = None
    country_iso3: str | None = None
    country_name: str | None = None
    region: str | None = None

    severity: float = 0
    relevance: float = 0
    confidence: float = 0
    source_reliability: float = 0
    materiality_score: float = 0

    direction: str = "neutral"
    event_time: str | None = None
    source_key: str | None = None
    evidence_url: str | None = None

    source_published_at: str | None = None
    source_retrieved_at: str | None = None
    observation_date: str | None = None
    freshness_type: str | None = None
    source_category: str | None = None
    is_structural: bool = False
    is_live: bool = False

    entities: list[dict[str, Any]] = field(default_factory=list)
    indicators: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class AgentAssessment:
    agent_key: str
    title: str
    bluf: str
    executive_summary: str

    risk_score: float
    risk_level: str
    confidence: float

    analytical_status: str
    key_drivers: list[dict[str, Any]]
    indicators: list[dict[str, Any]]
    forecast_probabilities: dict[str, float]
    implications: list[str]
    recommendations: list[str]
    intelligence_gaps: list[str]
    related_signal_ids: list[str]

    country_iso3: str | None = None
    country_name: str | None = None
    region: str | None = None

    generated_at: str = field(default_factory=utc_now_iso)

    assessment_generated_at: str | None = None
    latest_evidence_at: str | None = None
    oldest_material_evidence_at: str | None = None
    freshness_status: str = "unknown"
    evidence_composition: dict[str, int] = field(
        default_factory=dict
    )
    source_freshness: list[dict[str, Any]] = field(
        default_factory=list
    )


class BaseStrategicAgent(ABC):
    agent_key: str
    domain: str
    scoring_version: str = "strategic-agent-v1"

    @abstractmethod
    async def collect_signals(
        self,
        context: dict[str, Any],
    ) -> list[AgentSignal]:
        raise NotImplementedError

    @abstractmethod
    async def analyze(
        self,
        signals: list[AgentSignal],
        context: dict[str, Any],
    ) -> AgentAssessment:
        raise NotImplementedError

    async def run(
        self,
        context: dict[str, Any] | None = None,
    ) -> AgentAssessment:
        safe_context = context or {}
        signals = await self.collect_signals(safe_context)
        assessment = await self.analyze(signals, safe_context)

        metadata = self.build_freshness_metadata(
            signals=signals,
            assessment=assessment,
            context=safe_context,
        )

        assessment.assessment_generated_at = (
            assessment.generated_at
        )
        assessment.latest_evidence_at = metadata[
            "latest_evidence_at"
        ]
        assessment.oldest_material_evidence_at = metadata[
            "oldest_material_evidence_at"
        ]
        assessment.freshness_status = metadata[
            "freshness_status"
        ]
        assessment.evidence_composition = metadata[
            "evidence_composition"
        ]
        assessment.source_freshness = metadata[
            "source_freshness"
        ]

        return assessment

    @staticmethod
    def _parse_datetime(
        value: str | None,
    ) -> datetime | None:
        """
        Parse evidence timestamps into timezone-aware UTC datetimes.

        Supports both ISO-8601 timestamps used by internal services and
        RFC 2822 / HTTP-style timestamps commonly returned by RSS and
        news feeds.
        """
        if not value:
            return None

        normalized = str(value).strip()

        if not normalized:
            return None

        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except (TypeError, ValueError):
            try:
                parsed = parsedate_to_datetime(normalized)
            except (TypeError, ValueError, OverflowError):
                return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    def build_freshness_metadata(
        self,
        *,
        signals: list[AgentSignal],
        assessment: AgentAssessment,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        live_count = 0
        recent_count = 0
        structural_count = 0
        unknown_count = 0

        evidence_times: list[datetime] = []
        source_rows: list[dict[str, Any]] = []

        structural_sources = {
            "world bank",
            "imf",
            "eia baseline",
        }

        for signal in signals:
            source_name = str(
                signal.source_key or "Unknown source"
            ).strip()

            event_value = (
                signal.source_published_at
                or signal.observation_date
                or signal.event_time
            )

            evidence_time = self._parse_datetime(
                event_value
            )

            if evidence_time:
                evidence_times.append(evidence_time)

            source_lower = source_name.lower()

            is_structural = bool(
                signal.is_structural
                or signal.freshness_type == "structural"
                or source_lower in structural_sources
                or source_lower.startswith("world bank")
            )

            is_live = bool(
                signal.is_live
                or signal.freshness_type == "live"
            )

            if is_structural:
                freshness_type = "structural"
                structural_count += 1
            elif is_live:
                freshness_type = "live"
                live_count += 1
            elif evidence_time:
                age_hours = max(
                    0.0,
                    (now - evidence_time).total_seconds()
                    / 3600,
                )

                if age_hours <= 24:
                    freshness_type = "live"
                    live_count += 1
                elif age_hours <= 720:
                    freshness_type = "recent"
                    recent_count += 1
                else:
                    freshness_type = "structural"
                    structural_count += 1
            else:
                freshness_type = "unknown"
                unknown_count += 1

            source_rows.append(
                {
                    "source_name": source_name,
                    "source_category": (
                        signal.source_category
                        or signal.signal_type
                    ),
                    "latest_observation_at": event_value,
                    "retrieved_at": (
                        signal.source_retrieved_at
                    ),
                    "freshness_type": freshness_type,
                    "is_structural": is_structural,
                    "is_live": is_live,
                }
            )

        latest_evidence = (
            max(evidence_times).isoformat()
            if evidence_times
            else None
        )

        oldest_evidence = (
            min(evidence_times).isoformat()
            if evidence_times
            else None
        )

        insufficient_evidence = (
            assessment.risk_score == 0
            and assessment.confidence <= 30
            and not assessment.key_drivers
        )

        if insufficient_evidence:
            freshness_status = "insufficient_evidence"
        elif not signals:
            freshness_status = "unknown"
        elif structural_count == len(signals):
            freshness_status = "structural_baseline"
        elif structural_count > 0:
            freshness_status = "partially_current"
        elif latest_evidence:
            latest_dt = self._parse_datetime(
                latest_evidence
            )
            threshold_hours = float(
                context.get(
                    "freshness_threshold_hours",
                    24,
                )
            )

            if (
                latest_dt
                and (now - latest_dt).total_seconds()
                / 3600
                <= threshold_hours
            ):
                freshness_status = "current"
            else:
                freshness_status = "stale"
        else:
            freshness_status = "unknown"

        return {
            "latest_evidence_at": latest_evidence,
            "oldest_material_evidence_at": oldest_evidence,
            "freshness_status": freshness_status,
            "evidence_composition": {
                "live_signals": live_count,
                "recent_indicators": recent_count,
                "structural_indicators": structural_count,
                "unknown_evidence": unknown_count,
                "total_evidence": len(signals),
            },
            "source_freshness": source_rows,
        }

    @staticmethod
    def clamp_score(value: float) -> float:
        return round(max(0, min(100, value)), 2)

    @staticmethod
    def risk_level(score: float) -> str:
        if score >= 85:
            return "Critical"
        if score >= 70:
            return "High"
        if score >= 50:
            return "Elevated"
        if score >= 30:
            return "Watch"
        return "Low"

    @staticmethod
    def analytical_status(score: float) -> str:
        if score >= 70:
            return "alert"
        if score >= 40:
            return "watch"
        return "nominal"
