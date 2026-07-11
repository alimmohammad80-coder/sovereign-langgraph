from __future__ import annotations

from typing import Any

from app.intelligence.storage import get_supabase_client


MATERIAL_SCORE_DELTA = 5.0
MATERIAL_CONFIDENCE_DELTA = 10.0
CRITICAL_DRIVER_SEVERITY = 70.0


def load_latest_assessment(
    *,
    agent_key: str,
    country_iso3: str | None,
    region: str | None,
) -> dict[str, Any] | None:
    client = get_supabase_client()

    if client is None:
        return None

    query = (
        client.table("strategic_agent_outputs")
        .select("*")
        .eq("agent_key", agent_key)
    )

    if country_iso3:
        query = query.eq(
            "country_iso3",
            country_iso3.strip().upper(),
        )

    if region:
        query = query.eq(
            "region",
            region.strip(),
        )

    result = (
        query
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    return dict(result.data[0])


def _assessment_direction(
    assessment: dict[str, Any],
) -> str:
    drivers = assessment.get("key_drivers") or []
    indicators = assessment.get("indicators") or []

    if (
        float(assessment.get("risk_score") or 0) == 0
        and float(assessment.get("confidence") or 0) <= 30
        and not drivers
    ):
        return "unknown"

    directions = {
        str(item.get("direction") or "").strip().lower()
        for item in [*drivers, *indicators]
        if isinstance(item, dict)
    }

    if "deteriorating" in directions:
        return "deteriorating"

    if "improving" in directions:
        return "improving"

    if "neutral" in directions:
        return "neutral"

    presentation = (
        assessment.get("presentation_payload")
        or {}
    )

    analytical_status = str(
        assessment.get("analytical_status")
        or presentation.get("analytical_status")
        or ""
    ).lower()

    if analytical_status == "alert":
        return "deteriorating"

    return "unknown"


def _freshness_status(
    assessment: dict[str, Any],
) -> str:
    direct = assessment.get("freshness_status")

    if direct:
        return str(direct)

    presentation = (
        assessment.get("presentation_payload")
        or {}
    )

    return str(
        presentation.get("freshness_status")
        or "unknown"
    )


def _driver_identity(
    driver: dict[str, Any],
) -> str:
    return "|".join(
        (
            str(driver.get("headline") or "").strip().lower(),
            str(driver.get("source_key") or "").strip().lower(),
        )
    )


def detect_material_change(
    *,
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> dict[str, Any]:
    if previous is None:
        return {
            "material_change": True,
            "reasons": ["first_assessment_for_scope"],
            "score_delta": None,
            "confidence_delta": None,
            "previous_risk_level": None,
            "current_risk_level": current.get("risk_level"),
            "previous_direction": None,
            "current_direction": _assessment_direction(current),
        }

    reasons: list[str] = []

    previous_score = float(
        previous.get("risk_score") or 0
    )
    current_score = float(
        current.get("risk_score") or 0
    )
    score_delta = round(
        current_score - previous_score,
        2,
    )

    if abs(score_delta) >= MATERIAL_SCORE_DELTA:
        reasons.append("risk_score_changed")

    previous_level = str(
        previous.get("risk_level") or "Unknown"
    )
    current_level = str(
        current.get("risk_level") or "Unknown"
    )

    if previous_level != current_level:
        reasons.append("risk_level_changed")

    previous_confidence = float(
        previous.get("confidence") or 0
    )
    current_confidence = float(
        current.get("confidence") or 0
    )
    confidence_delta = round(
        current_confidence - previous_confidence,
        2,
    )

    if (
        abs(confidence_delta)
        >= MATERIAL_CONFIDENCE_DELTA
    ):
        reasons.append("confidence_changed")

    previous_direction = _assessment_direction(
        previous
    )
    current_direction = _assessment_direction(
        current
    )

    if previous_direction != current_direction:
        reasons.append("direction_changed")

    previous_freshness = _freshness_status(
        previous
    )
    current_freshness = _freshness_status(
        current
    )

    if (
        current_freshness
        in {"stale", "insufficient_evidence"}
        and current_freshness != previous_freshness
    ):
        reasons.append("freshness_degraded")

    previous_driver_ids = {
        _driver_identity(driver)
        for driver in (
            previous.get("key_drivers") or []
        )
        if isinstance(driver, dict)
    }

    new_critical_drivers = []

    for driver in current.get("key_drivers") or []:
        if not isinstance(driver, dict):
            continue

        severity = float(
            driver.get("severity") or 0
        )

        identity = _driver_identity(driver)

        if (
            severity >= CRITICAL_DRIVER_SEVERITY
            and identity not in previous_driver_ids
        ):
            new_critical_drivers.append(
                {
                    "headline": driver.get("headline"),
                    "severity": severity,
                    "source_key": driver.get("source_key"),
                }
            )

    if new_critical_drivers:
        reasons.append("new_high_severity_driver")

    return {
        "material_change": bool(reasons),
        "reasons": reasons,
        "score_delta": score_delta,
        "confidence_delta": confidence_delta,
        "previous_risk_level": previous_level,
        "current_risk_level": current_level,
        "previous_direction": previous_direction,
        "current_direction": current_direction,
        "previous_freshness": previous_freshness,
        "current_freshness": current_freshness,
        "new_critical_drivers": new_critical_drivers,
    }
