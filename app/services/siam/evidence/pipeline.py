from __future__ import annotations

from typing import Any

from app.agents.base_agent import AgentSignal
from app.services.siam.evidence.balancer import (
    RegionalEvidenceBalancer,
)
from app.services.siam.evidence.deduplicator import (
    EvidenceDeduplicator,
)
from app.services.siam.evidence.normalizer import (
    EvidenceNormalizer,
)
from app.services.siam.evidence.ranker import EvidenceRanker
from app.services.siam.evidence.scorer import EvidenceScorer
from app.services.siam.evidence.validator import EvidenceValidator


class REPPEvidencePipeline:
    """Regional Evidence Processing Pipeline."""

    @classmethod
    def run(
        cls,
        signals: list[AgentSignal],
        context: dict[str, Any] | None = None,
    ) -> list[AgentSignal]:
        safe_context = context or {}

        processed = EvidenceValidator.run(
            signals,
            safe_context,
        )
        processed = EvidenceNormalizer.run(
            processed,
            safe_context,
        )
        processed = EvidenceDeduplicator.run(
            processed,
            safe_context,
        )
        processed = RegionalEvidenceBalancer.run(
            processed,
            safe_context,
        )
        processed = EvidenceScorer.run(
            processed,
            safe_context,
        )
        processed = EvidenceRanker.run(
            processed,
            safe_context,
        )

        return processed
