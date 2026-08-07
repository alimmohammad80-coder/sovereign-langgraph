from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client

from app.services.sews_operational_intelligence_service import (
    SEWSOperationalIntelligenceService,
)


class SEWSExecutiveBriefService:
    """
    Produces the system-level Executive Brief for the
    SEWS Intelligence Engine.

    This service does not perform a separate forecast.
    It summarizes the current deterministic SEWS state.
    """

    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _warning_status(
        warnings: list[dict[str, Any]],
    ) -> str:
        if not warnings:
            return "NOT ASSESSED"

        probabilities = [
            float(row.get("probability") or 0)
            for row in warnings
        ]

        highest = max(probabilities, default=0)

        if highest >= 0.70:
            return "CRITICAL"

        if highest >= 0.45:
            return "HIGH"

        if highest >= 0.20:
            return "ELEVATED"

        return "LOW"

    @staticmethod
    def _confidence_text(
        warning: dict[str, Any],
    ) -> str:
        confidence = warning.get("confidence")

        if confidence is None:
            return "confidence is not yet assessable"

        confidence = float(confidence)

        if confidence <= 0:
            return "confidence is not yet assessable"

        return f"confidence is {confidence:.0f}%"

    def _build_summary(
        self,
        operational: dict[str, Any],
    ) -> str:
        warnings = operational.get("top_warnings") or []

        if not warnings:
            return (
                "SEWS currently has no completed warning "
                "assessments available for the executive brief."
            )

        highest = warnings[0]

        title = (
            highest.get("title")
            or highest.get("problem_key")
            or "the leading warning"
        )

        probability = float(
            highest.get("probability_percent")
            or (
                float(highest.get("probability") or 0)
                * 100
            )
        )

        confidence_text = self._confidence_text(
            highest
        )

        posture = (
            operational.get("system_posture")
            or {}
        )

        active_count = int(
            posture.get("active_warning_problems")
            or len(warnings)
        )

        material_changes = int(
            posture.get("material_change_count")
            or 0
        )

        propagation_count = int(
            posture.get("recent_propagation_count")
            or 0
        )

        regional = (
            operational.get("regional_posture")
            or []
        )

        leading_regions = sorted(
            regional,
            key=lambda row: float(
                row.get("highest_probability") or 0
            ),
            reverse=True,
        )[:3]

        region_text = ""

        if leading_regions:
            names = [
                str(row.get("region"))
                for row in leading_regions
                if row.get("region")
            ]

            if names:
                region_text = (
                    " The highest regional concentrations "
                    "of assessed warning activity are in "
                    + ", ".join(names)
                    + "."
                )

        return (
            f"SEWS is monitoring {active_count} active "
            f"warning problems across the global warning "
            f"portfolio. The leading assessed warning is "
            f"{title} at {probability:.1f}% probability; "
            f"{confidence_text}. "
            f"{material_changes} warnings have moved by at "
            f"least one percentage point since their prior "
            f"assessment, while {propagation_count} unique "
            f"cross-warning transmission events were "
            f"identified during the current 24-hour "
            f"operational window."
            f"{region_text} "
            f"The warning picture should be reviewed as "
            f"new evidence changes indicator activation, "
            f"corroboration, probability, or propagation "
            f"across the system."
        )

    def build(self) -> dict[str, Any]:
        operational = (
            SEWSOperationalIntelligenceService(
                self.db
            ).build(
                propagation_hours=24,
                warning_limit=52,
                product_limit=20,
            )
        )

        warnings = (
            operational.get("top_warnings")
            or []
        )

        posture = (
            operational.get("system_posture")
            or {}
        )

        pipeline = (
            posture.get("latest_pipeline_run")
            or {}
        )

        pipeline_status = str(
            pipeline.get("status")
            or "UNKNOWN"
        ).upper()

        if pipeline_status == "SUCCESS":
            system_status = "LIVE"
        elif pipeline_status in {
            "FAILED",
            "ERROR",
        }:
            system_status = "DEGRADED"
        else:
            system_status = "UNKNOWN"

        last_updated = (
            pipeline.get("finished_at")
            or operational.get("generated_at")
            or self._utcnow().isoformat()
        )

        status = self._warning_status(warnings)

        return {
            "status": "success",
            "generated_at": (
                self._utcnow().isoformat()
            ),
            "executive_summary": (
                self._build_summary(operational)
            ),
            "overall_warning_status": status,
            "last_updated": last_updated,
            "system_status": system_status,
            "metrics": {
                "active_warning_problems": (
                    posture.get(
                        "active_warning_problems"
                    )
                ),
                "material_changes": (
                    posture.get(
                        "material_change_count"
                    )
                ),
                "recent_propagations": (
                    posture.get(
                        "recent_propagation_count"
                    )
                ),
            },
            "source": (
                "SEWS operational intelligence engine"
            ),
        }
