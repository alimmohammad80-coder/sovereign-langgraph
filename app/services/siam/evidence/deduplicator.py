from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.agents.base_agent import AgentSignal


def _normalize_url(value: str | None) -> str:
    if not value:
        return ""

    try:
        parts = urlsplit(str(value).strip())
        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                "",
                "",
            )
        )
    except Exception:
        return str(value).strip().lower()


def _normalize_headline(value: str | None) -> str:
    text = str(value or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


class EvidenceDeduplicator:
    """Collapse duplicate evidence while preserving the strongest signal."""

    @staticmethod
    def run(
        signals: list[AgentSignal],
        context: dict[str, Any] | None = None,
    ) -> list[AgentSignal]:
        deduplicated: list[AgentSignal] = []
        seen: dict[str, AgentSignal] = {}

        for signal in signals:
            identity = (
                _normalize_url(signal.evidence_url)
                or _normalize_headline(signal.headline)
                or str(signal.signal_id or "").strip().lower()
            )

            if not identity:
                continue

            existing = seen.get(identity)

            if existing is None:
                setattr(
                    signal,
                    "siam_corroboration_count",
                    1,
                )
                seen[identity] = signal
                deduplicated.append(signal)
                continue

            corroboration_count = int(
                getattr(
                    existing,
                    "siam_corroboration_count",
                    1,
                )
            )

            setattr(
                existing,
                "siam_corroboration_count",
                corroboration_count + 1,
            )

            existing.severity = max(
                existing.severity,
                signal.severity,
            )
            existing.relevance = max(
                existing.relevance,
                signal.relevance,
            )
            existing.confidence = max(
                existing.confidence,
                signal.confidence,
            )
            existing.source_reliability = max(
                existing.source_reliability,
                signal.source_reliability,
            )
            existing.materiality_score = max(
                existing.materiality_score,
                signal.materiality_score,
            )

        return deduplicated
