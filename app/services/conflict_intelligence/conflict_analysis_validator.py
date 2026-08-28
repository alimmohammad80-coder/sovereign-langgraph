from __future__ import annotations

import re
import unicodedata
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

        #
        # Only accept numerical fields that are legitimately
        # expressed as percentages/scores in analytical prose.
        #
        allowed_key_terms = (
            "probability",
            "hazard",
            "confidence",
            "severity",
            "reliability",
            "score",
            "weight",
            "share",
            "effect",
            "risk",
            "intensity",
        )

        def walk(
            obj: Any,
            parent_key: str = "",
        ) -> None:

            if isinstance(obj, dict):

                for key, value in obj.items():

                    key_lower = str(
                        key
                    ).lower()

                    if isinstance(
                        value,
                        (int, float),
                    ) and not isinstance(
                        value,
                        bool,
                    ):

                        numeric = float(value)

                        metric_context = (
                            f"{parent_key} {key_lower}"
                        )

                        if any(
                            term in metric_context
                            for term in allowed_key_terms
                        ):
                            #
                            # Fractional metrics are typically
                            # stored as 0-1 but written as percent.
                            #
                            if 0.0 <= numeric <= 1.0:
                                values.add(
                                    round(
                                        numeric * 100,
                                        4,
                                    )
                                )

                            #
                            # Severity/confidence/reliability
                            # scores are already 0-100.
                            #
                            if 0.0 <= numeric <= 100.0:
                                values.add(
                                    round(
                                        numeric,
                                        4,
                                    )
                                )

                    if isinstance(
                        value,
                        (dict, list),
                    ):
                        walk(
                            value,
                            key_lower,
                        )

            elif isinstance(obj, list):

                for item in obj:
                    walk(
                        item,
                        parent_key,
                    )

        #
        # Ground only against authoritative analytical
        # sections. Do not whitelist arbitrary historical
        # years/counts merely because they are numbers.
        #
        authoritative_metrics = (
            packet.get(
                "authoritative_metrics"
            )
            or {}
        )

        walk(
            authoritative_metrics
        )

        #
        # Historical state percentages are already
        # deterministically calculated on a 0-100 scale.
        # Their keys are state codes rather than metric names,
        # so add them explicitly.
        #
        historical_state_percentages = (
            authoritative_metrics.get(
                "historical_state_percentages"
            )
            or {}
        )

        for value in (
            historical_state_percentages.values()
        ):
            if isinstance(
                value,
                (int, float),
            ) and not isinstance(
                value,
                bool,
            ):
                numeric = float(value)

                if 0.0 <= numeric <= 100.0:
                    values.add(
                        round(
                            numeric,
                            4,
                        )
                    )

        walk(
            (
                packet.get("conflict")
                or {}
            ).get(
                "current_state"
            )
            or {}
        )

        walk(
            packet.get(
                "current_evidence"
            )
            or {}
        )

        walk(
            packet.get(
                "forecast_models"
            )
            or {}
        )

        walk(
            packet.get(
                "ripple"
            )
            or {}
        )

        return values

    @staticmethod
    def _normalize_citation(
        value: str,
    ) -> str:

        value = unicodedata.normalize(
            "NFKC",
            str(value or ""),
        )

        value = (
            value
            .replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
        )

        value = re.sub(
            r"\\s+",
            " ",
            value,
        )

        return value.strip().rstrip(".")

    @classmethod
    def _allowed_sources(
        cls,
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
                    cls._normalize_citation(
                        citation
                    )
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

        historical_rows = (
            (
                packet.get("historical_context")
                or {}
            ).get("timeline")
            or []
        )

        historical_sources = {
            self._normalize_citation(
                str(row.get("source") or "")
            )
            for row in historical_rows
            if row.get("source")
        }

        conflict_id = packet.get(
            "conflict_id"
        )

        bad_references = []

        for ref in (
            report.get("references")
            or []
        ):
            citation = self._normalize_citation(
                ref.get("citation")
                or ""
            )

            if not citation:
                continue

            if citation in allowed_sources:
                continue

            # Historical timeline citations are valid only
            # when the cited dataset is actually present in
            # the authoritative packet and the citation refers
            # to this conflict.
            historical_match = False

            citation_lower = citation.lower()

            for source in historical_sources:
                source_lower = str(
                    source
                    or ""
                ).lower()

                if (
                    source_lower
                    and citation_lower.startswith(
                        source_lower
                    )
                ):
                    historical_match = True
                    break

            #
            # UCDP/PRIO is the authoritative historical
            # dataset in the packet. Accept normal Chicago-style
            # variants of that dataset citation when the packet
            # actually contains UCDP/PRIO historical rows.
            #
            if (
                not historical_match
                and "ucdp/prio" in citation_lower
                and any(
                    "ucdp/prio" in str(
                        source
                    ).lower()
                    for source in historical_sources
                )
            ):
                historical_match = True

            if not historical_match:
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

            is_active = (
                obs.get("active") is not False
            )

            if (
                is_active
                and (
                    source == "manual-test"
                    or payload.get("test") is True
                )
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
