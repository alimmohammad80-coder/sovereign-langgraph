from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
        return await self.analyze(signals, safe_context)

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
