from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.conflict_intelligence.conflict_event_classifier import (
    ConflictEventClassifier,
)
from app.services.conflict_intelligence.conflict_event_matcher import (
    ConflictEventMatcher,
)


class ConflictEvidenceEnricher:

    SOURCE_RELIABILITY = {
        "reuters": 95.0,
        "associated press": 95.0,
        "ap": 95.0,
        "bbc": 90.0,
        "bloomberg": 90.0,
        "financial times": 90.0,
        "new york times": 90.0,
        "washington post": 90.0,
        "united nations": 95.0,
        "un": 95.0,
        "world bank": 95.0,
        "imf": 95.0,
        "sipri": 95.0,
        "ucdp": 95.0,
    }

    def __init__(self) -> None:
        self.matcher = ConflictEventMatcher()

    @staticmethod
    def _citation(
        *,
        source_name: str,
        title: str,
        published_at: str | None,
        url: str | None,
    ) -> str:

        date_text = ""

        if published_at:
            try:
                dt = datetime.fromisoformat(
                    published_at.replace(
                        "Z",
                        "+00:00",
                    )
                )

                date_text = dt.strftime(
                    "%B %-d, %Y"
                )

            except Exception:
                date_text = str(
                    published_at
                )[:10]

        citation = (
            f'{source_name}, '
            f'"{title}"'
        )

        if date_text:
            citation += f", {date_text}"

        if url:
            citation += f", {url}"

        citation += "."

        return citation

    @classmethod
    def _source_reliability(
        cls,
        source_name: str | None,
    ) -> float:

        key = str(
            source_name or ""
        ).strip().lower()

        return cls.SOURCE_RELIABILITY.get(
            key,
            75.0,
        )

    @staticmethod
    def _severity(
        *,
        event_type: str,
        credibility_score: float | None,
    ) -> float:

        base = {
            "missile_strike": 90.0,
            "airstrike": 88.0,
            "armed_clash": 85.0,
            "military_activity": 70.0,
            "border_incident": 75.0,
            "terrorism": 75.0,
            "political_instability": 60.0,
            "sanctions": 55.0,
            "ceasefire": 50.0,
            "diplomatic_engagement": 40.0,
            "other": 35.0,
        }.get(
            event_type,
            35.0,
        )

        if credibility_score is None:
            return base

        normalized = min(
            max(
                float(
                    credibility_score
                ),
                0.0,
            ),
            10.0,
        )

        return round(
            base
            * (
                0.8
                + 0.2
                * (
                    normalized
                    / 10.0
                )
            ),
            1,
        )

    def enrich(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:

        title = str(
            event.get("title")
            or ""
        )

        summary = str(
            event.get("summary")
            or ""
        )

        match = self.matcher.match(
            title=title,
            summary=summary,
        )

        classification = (
            ConflictEventClassifier.classify(
                title=title,
                summary=summary,
            )
        )

        best = (
            match.get("best_match")
            or {}
        )

        credibility = event.get(
            "credibility_score"
        )

        confidence = (
            min(
                max(
                    float(
                        credibility
                    )
                    * 10.0,
                    0.0,
                ),
                100.0,
            )
            if credibility is not None
            else 70.0
        )

        source_name = str(
            event.get("source_name")
            or "Unknown"
        )

        published_at = event.get(
            "published_at"
        )

        url = event.get("url")

        return {
            "matched":
                bool(
                    match.get("matched")
                ),

            "conflict_id":
                best.get("conflict_id"),

            "canonical_episode_id":
                best.get(
                    "canonical_episode_id"
                ),

            "countries":
                match["entities"][
                    "country_iso3"
                ],

            "territories":
                match["entities"][
                    "territories"
                ],

            "event_type":
                classification[
                    "event_type"
                ],

            "supports_escalation":
                classification[
                    "supports_escalation"
                ],

            "contradicts_escalation":
                classification[
                    "contradicts_escalation"
                ],

            "severity":
                self._severity(
                    event_type=
                        classification[
                            "event_type"
                        ],
                    credibility_score=
                        credibility,
                ),

            "confidence":
                round(
                    confidence,
                    1,
                ),

            "source_reliability":
                self._source_reliability(
                    source_name
                ),

            "citation_text":
                self._citation(
                    source_name=
                        source_name,
                    title=title,
                    published_at=
                        published_at,
                    url=url,
                ),

            "match_details":
                match,

            "classification_details":
                classification,
        }
