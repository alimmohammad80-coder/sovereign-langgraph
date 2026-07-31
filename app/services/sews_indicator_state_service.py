from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from supabase import Client

from app.schemas.sews_evidence import (
    IndicatorStateRecalculateRequest,
    IndicatorStateResponse,
    WarningProblemStateResponse,
)


CALCULATION_VERSION = "sews-indicator-state-v1.0.0"


class SEWSIndicatorStateError(RuntimeError):
    pass


class SEWSIndicatorStateService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _state_key(request: IndicatorStateRecalculateRequest) -> str:
        context = "|".join(
            [
                request.indicator_key,
                request.warning_problem_key or "",
                request.analytic_framework_key or "",
                request.indicator_group_key or "",
                request.country_iso3 or "",
                request.region_key or "",
            ]
        )
        return f"IST-{hashlib.sha256(context.encode()).hexdigest()[:32]}"

    @staticmethod
    def _trend(current: float | None, previous: float | None) -> str:
        if current is None or previous is None:
            return "UNKNOWN"
        delta = current - previous
        if delta >= 0.05:
            return "RISING"
        if delta <= -0.05:
            return "FALLING"
        return "STABLE"

    @staticmethod
    def _confidence(
        *,
        evidence_count: int,
        source_count: int,
        reliability: float,
        freshness: float,
        contradiction_ratio: float,
    ) -> float:
        coverage = min(100.0, 25.0 * math.log2(evidence_count + 1))
        corroboration = min(100.0, source_count * 25.0)
        consistency = max(0.0, 100.0 * (1.0 - contradiction_ratio))
        score = (
            coverage * 0.25
            + corroboration * 0.20
            + reliability * 0.25
            + freshness * 0.15
            + consistency * 0.15
        )
        return round(max(0.0, min(100.0, score)), 2)

    def _query_observations(
        self, request: IndicatorStateRecalculateRequest
    ) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=request.lookback_days)
        query = (
            self.db.table("sews_observations")
            .select(
                "id,observation_key,normalized_value,polarity,trend,confidence,"
                "evidence_count,corroborated_source_count,source_reliability_mean,"
                "freshness_score,observed_at,status"
            )
            .eq("indicator_key", request.indicator_key)
            .eq("status", "VALIDATED")
            .gte("observed_at", since.isoformat())
        )
        for column, value in (
            ("warning_problem_key", request.warning_problem_key),
            ("analytic_framework_key", request.analytic_framework_key),
            ("indicator_group_key", request.indicator_group_key),
            ("country_iso3", request.country_iso3),
            ("region_key", request.region_key),
        ):
            if value is not None:
                query = query.eq(column, value)
            else:
                query = query.is_(column, "null")
        return query.order("observed_at", desc=True).execute().data or []

    def recalculate(
        self, request: IndicatorStateRecalculateRequest
    ) -> IndicatorStateResponse:
        observations = self._query_observations(request)
        now = datetime.now(timezone.utc)
        state_key = self._state_key(request)

        existing_result = (
            self.db.table("sews_indicator_state")
            .select("*")
            .eq("state_key", state_key)
            .limit(1)
            .execute()
        )
        existing = existing_result.data[0] if existing_result.data else None
        previous_value = (
            float(existing["current_value"])
            if existing and existing.get("current_value") is not None
            else None
        )

        usable = [
            row
            for row in observations
            if row.get("normalized_value") is not None
        ]
        evidence_count = sum(int(row.get("evidence_count") or 0) for row in usable)
        source_count = max(
            [int(row.get("corroborated_source_count") or 0) for row in usable]
            or [0]
        )
        supporting = sum(
            int(row.get("evidence_count") or 0)
            for row in usable
            if row["polarity"] == "SUPPORTING"
        )
        contradicting = sum(
            int(row.get("evidence_count") or 0)
            for row in usable
            if row["polarity"] == "CONTRADICTING"
        )

        if evidence_count < request.minimum_evidence or not usable:
            current_value = None
            confidence = 0.0
            freshness = 0.0
            status = "INSUFFICIENT_EVIDENCE"
            latest_observation_id = usable[0]["id"] if usable else None
            last_observed_at = usable[0]["observed_at"] if usable else None
        else:
            weighted_total = 0.0
            total_weight = 0.0
            reliability_values = []
            freshness_values = []

            for row in usable:
                value = float(row["normalized_value"])
                # Contradicting observations reduce the signal deterministically.
                if row["polarity"] == "CONTRADICTING":
                    value = 1.0 - value
                elif row["polarity"] == "NEUTRAL":
                    continue

                reliability = float(row.get("source_reliability_mean") or 50)
                freshness_score = float(row.get("freshness_score") or 0)
                observation_confidence = float(row.get("confidence") or 0)
                weight = (
                    max(0.01, observation_confidence / 100)
                    * max(0.01, reliability / 100)
                    * max(0.01, freshness_score / 100)
                    * max(1, int(row.get("evidence_count") or 1))
                )
                weighted_total += value * weight
                total_weight += weight
                reliability_values.append(reliability)
                freshness_values.append(freshness_score)

            current_value = (
                round(weighted_total / total_weight, 4)
                if total_weight > 0
                else None
            )
            freshness = round(mean(freshness_values), 2) if freshness_values else 0.0
            reliability_mean = (
                round(mean(reliability_values), 2)
                if reliability_values
                else 0.0
            )
            contradiction_ratio = (
                contradicting / max(1, supporting + contradicting)
            )
            confidence = self._confidence(
                evidence_count=evidence_count,
                source_count=source_count,
                reliability=reliability_mean,
                freshness=freshness,
                contradiction_ratio=contradiction_ratio,
            )
            latest_observation_id = usable[0]["id"]
            last_observed_at = usable[0]["observed_at"]
            latest_time = datetime.fromisoformat(
                last_observed_at.replace("Z", "+00:00")
            )
            if latest_time.tzinfo is None:
                latest_time = latest_time.replace(tzinfo=timezone.utc)
            if now - latest_time > timedelta(hours=request.stale_after_hours):
                status = "STALE"
            elif confidence < 40:
                status = "DEGRADED"
            else:
                status = "ACTIVE"

        delta = (
            round(current_value - previous_value, 4)
            if current_value is not None and previous_value is not None
            else None
        )
        trend = self._trend(current_value, previous_value)
        stale_after = (
            (
                datetime.fromisoformat(last_observed_at.replace("Z", "+00:00"))
                + timedelta(hours=request.stale_after_hours)
            ).isoformat()
            if last_observed_at
            else None
        )

        row = {
            "state_key": state_key,
            "indicator_key": request.indicator_key,
            "warning_problem_key": request.warning_problem_key,
            "analytic_framework_key": request.analytic_framework_key,
            "indicator_group_key": request.indicator_group_key,
            "country_iso3": request.country_iso3,
            "region_key": request.region_key,
            "current_value": current_value,
            "previous_value": previous_value,
            "delta": delta,
            "trend": trend,
            "confidence": confidence,
            "evidence_count": evidence_count,
            "supporting_evidence_count": supporting,
            "contradicting_evidence_count": contradicting,
            "corroborated_source_count": source_count,
            "freshness_score": freshness,
            "latest_observation_id": latest_observation_id,
            "status": status,
            "stale_after": stale_after,
            "last_observed_at": last_observed_at,
            "last_calculated_at": now.isoformat(),
            "calculation_version": CALCULATION_VERSION,
            "state_metadata": {
                "lookback_days": request.lookback_days,
                "minimum_evidence": request.minimum_evidence,
                "observation_count": len(usable),
            },
        }

        result = (
            self.db.table("sews_indicator_state")
            .upsert(row, on_conflict="state_key")
            .execute()
        )
        if not result.data:
            raise SEWSIndicatorStateError(
                "Indicator-state upsert returned no row."
            )
        return IndicatorStateResponse(**result.data[0])

    def get_state(
        self,
        indicator_key: str,
        *,
        warning_problem_key: str | None = None,
        country_iso3: str | None = None,
        region_key: str | None = None,
    ) -> dict[str, Any] | None:
        query = (
            self.db.table("sews_current_indicator_state")
            .select("*")
            .eq("indicator_key", indicator_key)
        )
        if warning_problem_key:
            query = query.eq("warning_problem_key", warning_problem_key)
        if country_iso3:
            query = query.eq("country_iso3", country_iso3.upper())
        if region_key:
            query = query.eq("region_key", region_key)
        result = query.order("last_calculated_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    def warning_problem_state(
        self, warning_problem_key: str
    ) -> WarningProblemStateResponse:
        result = (
            self.db.table("sews_current_indicator_state")
            .select("*")
            .eq("warning_problem_key", warning_problem_key)
            .execute()
        )
        states = result.data or []
        values = [
            float(row["current_value"])
            for row in states
            if row.get("current_value") is not None
        ]
        confidences = [
            float(row["confidence"])
            for row in states
            if row.get("confidence") is not None
        ]
        return WarningProblemStateResponse(
            warning_problem_key=warning_problem_key,
            indicator_count=len(states),
            active_count=sum(row["status"] == "ACTIVE" for row in states),
            insufficient_evidence_count=sum(
                row["status"] == "INSUFFICIENT_EVIDENCE" for row in states
            ),
            degraded_count=sum(row["status"] == "DEGRADED" for row in states),
            stale_count=sum(row["status"] == "STALE" for row in states),
            mean_value=round(mean(values), 4) if values else None,
            mean_confidence=round(mean(confidences), 2)
            if confidences
            else None,
            states=states,
        )
