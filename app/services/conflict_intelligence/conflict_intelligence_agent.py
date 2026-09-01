from __future__ import annotations

import asyncio
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.canonical_conflict_resolver import (
    CanonicalConflictResolver,
)

from app.services.conflict_intelligence.analysis_packet_builder import (
    ConflictAnalysisPacketBuilder,
)

from app.services.conflict_intelligence.conflict_evidence_observation_bridge import (
    ConflictEvidenceObservationBridge,
)


from app.services.conflict_intelligence.conflict_collection_orchestrator import (
    ConflictCollectionOrchestrator,
)


class ConflictIntelligenceAgent:
    """
    Governed orchestration layer for Conflict Intelligence.

    Responsibilities:

    1. Normalize the user's analytical request.
    2. Resolve canonical conflict context when available.
    3. Gather baseline conflict data.
    4. Gather current observations and evidence.
    5. Run/retrieve deterministic forecast data when applicable.
    6. Produce one grounded intelligence packet for the LLM analyst.

    The agent does NOT invent probabilities.
    """

    AGENT_VERSION = (
        "conflict-intelligence-agent-v1"
    )

    def __init__(self) -> None:

        self.db = (
            get_supabase_client()
        )

        self.resolver = (
            CanonicalConflictResolver()
        )

        self.packet_builder = (
            ConflictAnalysisPacketBuilder()
        )

    @staticmethod
    def _normalize_countries(
        countries: list[str],
    ) -> list[str]:

        return sorted({
            str(value)
            .strip()
            .upper()
            for value in countries
            if value
        })

    def _resolve_conflict(
        self,
        countries: list[str],
    ) -> dict[str, Any] | None:

        if len(countries) != 2:
            return None

        try:

            result = (
                self.resolver.resolve(
                    participant_a=
                        countries[0],

                    participant_b=
                        countries[1],
                )
            )

        except Exception:
            return None

        if not result.get(
            "matched"
        ):
            return None

        return result

    def _baseline(
        self,
        countries: list[str],
        conflict_type: str | None,
    ) -> list[dict[str, Any]]:

        rows = (
            self.db.table(
                "conflict_canonical_episodes"
            )
            .select("*")
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        requested = set(
            countries
        )

        results = []

        for row in rows:

            participants = {
                str(value)
                .strip()
                .upper()
                for value in (
                    row.get(
                        "state_participants"
                    )
                    or []
                )
                if value
            }

            if not (
                participants
                .intersection(
                    requested
                )
            ):
                continue

            if conflict_type:

                row_type = str(
                    row.get(
                        "conflict_type"
                    )
                    or ""
                ).lower()

                requested_type = (
                    conflict_type
                    .strip()
                    .lower()
                )

                if (
                    requested_type
                    and requested_type
                    not in row_type
                ):
                    # Do not eliminate baseline
                    # simply because legacy UCDP
                    # type coding is numeric.
                    pass

            results.append(
                row
            )

        return results[:100]

    def _current_observations(
        self,
        countries: list[str],
        indicators: list[str],
        conflict_id: int | None = None,
    ) -> list[dict[str, Any]]:

        rows = (
            self.db.table(
                "conflict_observations"
            )
            .select("*")
            .eq("active", True)
            .order("observed_at", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )

        requested = set(countries)
        results = []

        for row in rows:

            row_conflict_id = row.get("conflict_id")

            if (
                conflict_id is not None
                and row_conflict_id is not None
            ):
                if int(row_conflict_id) != int(conflict_id):
                    continue

                results.append(row)
                continue

            country = str(
                row.get("country_iso3")
                or ""
            ).upper()

            related = {
                str(value).strip().upper()
                for value in (
                    row.get("related_state_iso3")
                    or []
                )
                if value
            }

            if (
                country not in requested
                and not related.intersection(requested)
            ):
                continue

            results.append(row)

        return results[:100]

    def _current_evidence(
        self,
        countries: list[str],
        conflict_id: int | None = None,
    ) -> list[dict[str, Any]]:

        rows = (
            self.db.table(
                "conflict_evidence"
            )
            .select("*")
            .order("published_at", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )

        requested = set(countries)
        results = []

        for row in rows:

            row_conflict_id = row.get("conflict_id")

            if (
                conflict_id is not None
                and row_conflict_id is not None
            ):
                if int(row_conflict_id) == int(conflict_id):
                    results.append(row)

                continue

            country = str(
                row.get("country_iso3")
                or ""
            ).upper()

            related = {
                str(value).strip().upper()
                for value in (
                    row.get("related_state_iso3")
                    or []
                )
                if value
            }

            if (
                country in requested
                or related.intersection(requested)
            ):
                results.append(row)

        return results[:100]


    async def collect_current_intelligence(
        self,
        *,
        countries: list[str],
        region: str | None,
        conflict_type: str | None,
        indicators: list[str],
    ) -> dict[str, Any]:

        country_rows = (
            self.db.table("conflict_countries")
            .select("iso3,name")
            .in_("iso3", countries)
            .execute()
            .data
            or []
        )

        country_names = {
            str(row.get("iso3") or "").upper():
                str(row.get("name") or "")
            for row in country_rows
        }

        parts = [
            country_names.get(code, code)
            for code in countries
        ]

        parts.append("conflict")

        query = " ".join(
            str(value).strip()
            for value in parts
            if value
        )

        return await (
            ConflictCollectionOrchestrator()
            .run(
                query=query,
                limit_per_source=25,
            )
        )

    def build_packet(
        self,
        *,
        countries: list[str],
        region: str | None,
        conflict_type: str | None,
        indicators: list[str],
        horizon_days: int,
        lookback_days: int,
        ripple_depth: int,
    ) -> dict[str, Any]:

        countries = (
            self._normalize_countries(
                countries
            )
        )

        resolved = (
            self._resolve_conflict(
                countries
            )
        )

        try:
            live_collection = asyncio.run(
                self.collect_current_intelligence(
                    countries=countries,
                    region=region,
                    conflict_type=conflict_type,
                    indicators=indicators,
                )
            )
        except Exception as exc:
            live_collection = {
                "status": "failed",
                "error": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            }

        deterministic_packet = None
        observation_promotion = None

        if resolved:

            conflict_id = int(
                resolved[
                    "conflict_id"
                ]
            )

            # Live intelligence collection writes governed conflict evidence.
            # Promote that evidence into deterministic observations and
            # recompute the current conflict state BEFORE forecast models run.
            #
            # This is conflict-agnostic and uses the existing canonical
            # resolution, observation ingestion, and state-engine rules.
            try:
                observation_promotion = (
                    ConflictEvidenceObservationBridge()
                    .run(
                        conflict_id=conflict_id,
                        limit=500,
                        recompute_state=True,
                    )
                )
            except Exception as exc:
                observation_promotion = {
                    "status": "failed",
                    "error": (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                }

            try:

                deterministic_packet = (
                    self.packet_builder
                    .build(
                        conflict_id=
                            conflict_id,

                        horizon_days=
                            horizon_days,

                        lookback_days=
                            lookback_days,

                        ripple_depth=
                            ripple_depth,
                    )
                )

            except Exception as exc:

                deterministic_packet = {
                    "available":
                        False,

                    "error":
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                }

        return {
            "packet_version":
                "conflict-agent-packet-v1",

            "agent_version":
                self.AGENT_VERSION,

            "request": {
                "countries":
                    countries,

                "region":
                    region,

                "conflict_type":
                    conflict_type,

                "indicators":
                    indicators,

                "horizon_days":
                    horizon_days,

                "lookback_days":
                    lookback_days,
            },

            "canonical_resolution":
                resolved,

            "live_collection":
                live_collection,

            "observation_promotion":
                observation_promotion,

            "baseline_conflict_data":
                self._baseline(
                    countries,
                    conflict_type,
                ),

            "current_observations":
                self._current_observations(
                    countries,
                    indicators,
                    (
                        int(resolved["conflict_id"])
                        if resolved
                        else None
                    ),
                ),

            "current_evidence":
                self._current_evidence(
                    countries,
                    (
                        int(resolved["conflict_id"])
                        if resolved
                        else None
                    ),
                ),

            "deterministic_analysis":
                deterministic_packet,

            "governance": {
                "llm_may_interpret":
                    True,

                "llm_may_create_probabilities":
                    False,

                "deterministic_models_are_authoritative":
                    True,

                "absence_of_evidence_is_not_evidence_of_absence":
                    True,
            },
        }
