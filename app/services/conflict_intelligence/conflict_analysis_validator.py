from __future__ import annotations

import re
from typing import Any


class ConflictAnalysisValidator:

    REQUIRED_KEYS = {
        "bluf",
        "executive_judgment",
        "current_situation",
        "key_drivers",
        "contrary_evidence",
        "historical_context",
        "escalation_pathways",
        "forecast_outlook",
        "indicators_to_watch",
        "strategic_implications",
        "confidence_assessment",
        "full_analysis",
        "references",
    }

    @staticmethod
    def _extract_percentages(
        value: Any,
    ) -> list[float]:

        text = str(value or "")

        matches = re.findall(
            r"(\d+(?:\.\d+)?)\s*%",
            text,
        )

        return [
            round(float(x), 4)
            for x in matches
        ]

    @staticmethod
    def _packet_probabilities(
        packet: dict[str, Any],
    ) -> set[float]:

        values: set[float] = set()

        def walk(obj: Any) -> None:

            if isinstance(obj, dict):
                for key, value in obj.items():

                    if isinstance(
                        value,
                        (int, float),
                    ):
                        key_lower = str(
                            key
                        ).lower()

                        if (
                            "probability" in key_lower
                            or "hazard" in key_lower
                        ):
                            numeric = float(value)

                            if 0 <= numeric <= 1:
                                values.add(
                                    round(
                                        numeric * 100,
                                        4,
                                    )
                                )

                    walk(value)

            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(
            packet.get(
                "authoritative_metrics"
            )
        )

        walk(
            packet.get(
                "forecast_models"
            )
        )

        return values

    @staticmethod
    def _allowed_sources(
        packet: dict[str, Any],
    ) -> set[str]:

        citations = set()

        for item in (
            packet.get("sources")
            or []
        ):
            citation = item.get(
                "citation_text"
            )

            if citation:
                citations.add(
                    str(citation).strip()
                )

        return citations

    def validate(
        self,
        *,
        report: dict[str, Any],
        packet: dict[str, Any],
    ) -> dict[str, Any]:

        checks = {}

        missing = (
            self.REQUIRED_KEYS
            - set(report.keys())
        )

        checks[
            "required_sections"
        ] = not missing

        allowed_probabilities = (
            self._packet_probabilities(
                packet
            )
        )

        report_percentages = []

        for key, value in report.items():
            if key == "references":
                continue

            report_percentages.extend(
                self._extract_percentages(
                    value
                )
            )

        unsupported_percentages = []

        for value in report_percentages:

            if not any(
                abs(
                    value
                    - allowed
                ) <= 0.15
                for allowed in allowed_probabilities
            ):
                unsupported_percentages.append(
                    value
                )

        checks[
            "probability_grounding"
        ] = (
            len(
                unsupported_percentages
            )
            == 0
        )

        allowed_sources = (
            self._allowed_sources(
                packet
            )
        )

        bad_references = []

        for ref in (
            report.get("references")
            or []
        ):
            citation = str(
                ref.get("citation")
                or ""
            ).strip()

            if (
                citation
                and citation
                not in allowed_sources
            ):
                bad_references.append(
                    citation
                )

        checks[
            "reference_grounding"
        ] = (
            len(bad_references)
            == 0
        )

        active_test_evidence = []

        for obs in (
            packet.get(
                "current_evidence",
                {}
            ).get(
                "observations",
                []
            )
            or []
        ):
            source = str(
                obs.get("source")
                or ""
            ).lower()

            payload = (
                obs.get(
                    "observation_data"
                )
                or {}
            )

            if (
                source == "manual-test"
                or payload.get("test") is True
            ):
                active_test_evidence.append(
                    obs.get(
                        "observation_key"
                    )
                )

        checks[
            "no_test_evidence"
        ] = (
            len(
                active_test_evidence
            )
            == 0
        )

        passed = all(
            checks.values()
        )

        return {
            "passed":
                passed,

            "checks":
                checks,

            "missing_sections":
                sorted(missing),

            "unsupported_percentages":
                unsupported_percentages,

            "bad_references":
                bad_references,

            "active_test_evidence":
                active_test_evidence,
        }
