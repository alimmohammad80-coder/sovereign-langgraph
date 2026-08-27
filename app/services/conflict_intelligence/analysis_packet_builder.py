from __future__ import annotations

from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.conflict_forecast_ensemble import (
    ConflictForecastEnsemble,
)

from app.services.conflict_intelligence.conflict_transition_forecaster import (
    ConflictTransitionForecaster,
)

from app.services.conflict_intelligence.dyadic_escalation_model import (
    DyadicEscalationModel,
)

from app.services.conflict_intelligence.frozen_conflict_hazard_model import (
    FrozenConflictHazardModel,
)

from app.services.conflict_intelligence.hawkes_escalation_model import (
    HawkesEscalationModel,
)

from app.services.conflict_intelligence.pre_conflict_escalation_model import (
    PreConflictEscalationModel,
)

from app.services.conflict_intelligence.ripple_propagation_engine import (
    RipplePropagationEngine,
)


class ConflictAnalysisPacketBuilder:

    PACKET_VERSION = "conflict-analysis-packet-v1"

    def __init__(self) -> None:
        self.db = get_supabase_client()

    def _current_state(
        self,
        conflict_id: int,
    ) -> dict[str, Any] | None:

        rows = (
            self.db.table(
                "conflict_current_state"
            )
            .select("*")
            .eq(
                "conflict_id",
                conflict_id,
            )
            .order(
                "calculated_at",
                desc=True,
            )
            .limit(1)
            .execute()
            .data
            or []
        )

        return rows[0] if rows else None

    def _historical_episode(
        self,
        conflict_id: int,
    ) -> dict[str, Any] | None:

        rows = (
            self.db.table(
                "conflict_historical_episodes"
            )
            .select("*")
            .eq(
                "conflict_id",
                conflict_id,
            )
            .limit(1)
            .execute()
            .data
            or []
        )

        return rows[0] if rows else None

    def _timeline(
        self,
        conflict_id: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        return (
            self.db.table(
                "conflict_state_timeline"
            )
            .select("*")
            .eq(
                "conflict_id",
                conflict_id,
            )
            .order(
                "year",
                desc=False,
            )
            .limit(limit)
            .execute()
            .data
            or []
        )

    def _observations(
        self,
        conflict_id: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        return (
            self.db.table(
                "conflict_observations"
            )
            .select("*")
            .eq(
                "conflict_id",
                conflict_id,
            )
            .order(
                "observed_at",
                desc=True,
            )
            .limit(limit)
            .execute()
            .data
            or []
        )

    def _evidence(
        self,
        conflict_id: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        try:
            return (
                self.db.table(
                    "conflict_evidence"
                )
                .select("*")
                .eq(
                    "conflict_id",
                    conflict_id,
                )
                .eq(
                    "active",
                    True,
                )
                .order(
                    "observed_at",
                    desc=True,
                )
                .limit(limit)
                .execute()
                .data
                or []
            )
        except Exception:
            return []

    def _safe_model(
        self,
        fn,
    ) -> dict[str, Any]:

        try:
            return fn()
        except Exception as exc:
            return {
                "available": False,
                "error": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            }

    def build(
        self,
        conflict_id: int,
        horizon_days: int = 365,
        lookback_days: int = 90,
        ripple_depth: int = 3,
    ) -> dict[str, Any]:

        current_state = self._current_state(
            conflict_id
        )

        historical_episode = (
            self._historical_episode(
                conflict_id
            )
        )

        timeline = self._timeline(
            conflict_id
        )

        observations = self._observations(
            conflict_id
        )

        evidence = self._evidence(
            conflict_id
        )

        ensemble = self._safe_model(
            lambda: ConflictForecastEnsemble()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        horizons = self._safe_model(
            lambda: ConflictTransitionForecaster()
            .forecast_all_horizons(
                conflict_id
            )
        )

        preconflict = self._safe_model(
            lambda: PreConflictEscalationModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        dyadic = self._safe_model(
            lambda: DyadicEscalationModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        frozen = self._safe_model(
            lambda: FrozenConflictHazardModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        hawkes = self._safe_model(
            lambda: HawkesEscalationModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        ripple = self._safe_model(
            lambda: RipplePropagationEngine()
            .run(
                conflict_id=conflict_id,
                horizon_days=horizon_days,
                lookback_days=lookback_days,
                max_depth=ripple_depth,
            )
        )

        sources = []

        for item in evidence:
            sources.append(
                {
                    "source_name":
                        item.get("source_name"),

                    "source_url":
                        item.get("source_url"),

                    "citation_text":
                        item.get("citation_text"),

                    "source_type":
                        item.get("source_type"),

                    "source_reliability":
                        item.get(
                            "source_reliability"
                        ),
                }
            )

        def evidence_strength(
            item: dict[str, Any],
        ) -> float:

            severity = float(
                item.get("severity")
                or 0.0
            )

            confidence = float(
                item.get("confidence")
                or 0.0
            )

            reliability = float(
                item.get("source_reliability")
                or 0.0
            )

            return (
                0.40 * severity
                + 0.35 * confidence
                + 0.25 * reliability
            )

        ranked_evidence = sorted(
            evidence,
            key=evidence_strength,
            reverse=True,
        )

        escalatory_evidence = [
            item
            for item in ranked_evidence
            if item.get("supports_escalation") is True
        ][:10]

        contrary_evidence = [
            item
            for item in ranked_evidence
            if item.get("contradicts_escalation") is True
        ][:10]

        neutral_evidence = [
            item
            for item in ranked_evidence
            if (
                item.get("supports_escalation") is not True
                and item.get("contradicts_escalation") is not True
            )
        ][:10]

        event_type_counts = {}

        for item in evidence:
            key = str(
                item.get("event_type")
                or "other"
            )

            event_type_counts[key] = (
                event_type_counts.get(
                    key,
                    0,
                )
                + 1
            )

        unique_sources = {}

        for source in sources:
            key = (
                source.get("source_url")
                or source.get("citation_text")
                or source.get("source_name")
            )

            if key:
                unique_sources[
                    str(key)
                ] = source

        sources = list(
            unique_sources.values()
        )

        historical_state_counts = {}

        for row in timeline:
            state_code = str(
                row.get("state_code")
                or "UNKNOWN"
            )

            historical_state_counts[
                state_code
            ] = (
                historical_state_counts.get(
                    state_code,
                    0,
                )
                + 1
            )

        authoritative_metrics = {
            "current_state": (
                current_state.get("state_code")
                if current_state
                else None
            ),

            "current_state_escalation_probability": (
                current_state.get(
                    "escalation_probability"
                )
                if current_state
                else None
            ),

            "current_state_probability_source":
                "conflict-state-v1",

            "current_confidence": (
                current_state.get("confidence")
                if current_state
                else None
            ),

            "historical_year_count":
                len(timeline),

            "historical_state_counts":
                historical_state_counts,
        }

        return {
            "packet_version":
                self.PACKET_VERSION,

            "conflict_id":
                conflict_id,

            "conflict":
                {
                    "historical_episode":
                        historical_episode,

                    "current_state":
                        current_state,
                },

            "historical_context":
                {
                    "timeline":
                        timeline,

                    "timeline_count":
                        len(timeline),
                },

            "current_evidence":
                {
                    "observations":
                        observations,

                    "observation_count":
                        len(observations),

                    "evidence":
                        evidence,

                    "evidence_count":
                        len(evidence),

                    "event_type_counts":
                        event_type_counts,

                    "strongest_escalatory":
                        escalatory_evidence,

                    "strongest_contrary":
                        contrary_evidence,

                    "strongest_neutral":
                        neutral_evidence,
                },

            "authoritative_metrics":
                authoritative_metrics,

            "forecast_models":
                {
                    "ensemble":
                        ensemble,

                    "horizons":
                        horizons,

                    "preconflict":
                        preconflict,

                    "dyadic":
                        dyadic,

                    "frozen_hazard":
                        frozen,

                    "hawkes":
                        hawkes,
                },

            "ripple":
                ripple,

            "sources":
                sources,

            "analysis_rules":
                {
                    "quantitative_forecast_is_authoritative":
                        True,

                    "ai_may_not_recalculate_probability":
                        True,

                    "must_distinguish_fact_from_inference":
                        True,

                    "must_include_contrary_evidence":
                        True,

                    "must_use_available_citations":
                        True,

                    "citation_style":
                        "Chicago Notes and Bibliography",
                },
        }
