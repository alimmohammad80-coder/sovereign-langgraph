from __future__ import annotations

import copy
import re
from enum import StrEnum
from typing import Any


class AssessmentMode(StrEnum):
    ACTIVE = "ACTIVE"
    HISTORICAL_CONCLUDED = "HISTORICAL_CONCLUDED"
    FROZEN_UNRESOLVED = "FROZEN_UNRESOLVED"
    EMERGING = "EMERGING"


STATE_LABELS = {
    "S0_STABLE": "Stable",
    "S1_TENSION": "Heightened Tension",
    "S2_CRISIS": "Crisis",
    "S3_LIMITED_CONFLICT": "Limited Armed Conflict",
    "S4_WAR": "High-Intensity War",
    "S5_FROZEN": "Frozen or Unresolved Conflict",
}

SHORT_STATE_LABELS = {
    "S0": "Stable",
    "S1": "Heightened Tension",
    "S2": "Crisis",
    "S3": "Limited Armed Conflict",
    "S4": "High-Intensity War",
    "S5": "Frozen or Unresolved Conflict",
}

MODEL_PRESENTATION_REPLACEMENTS = [
    (
        r"\btemporal escalation assessment\s+temporal\s+"
        r"(?:point-process\s+)?model\b",
        "Temporal Escalation Model",
    ),
    (
        r"\btemporal escalation assessment\s+escalation\s+model\b",
        "Temporal Escalation Model",
    ),
    (
        r"\btemporal escalation assessment\s+model\b",
        "Temporal Escalation Model",
    ),
    (
        r"\binterstate escalation assessment\s+escalation\s+model\b",
        "Interstate Escalation Model",
    ),
    (
        r"\binterstate escalation assessment\s+model\b",
        "Interstate Escalation Model",
    ),
    (
        r"\bConflict-State Model\s+v\d+\b",
        "Conflict State Model",
    ),
    (
        r"\bEmpirical Annual Markov Model\s+v\d+\b",
        "Empirical Transition Model",
    ),
    (
        r"\bPre-Conflict Bayesian Logit\s+v\d+\b",
        "Pre-Conflict Escalation Model",
    ),
    (
        r"\bFrozen Conflict Hazard Model\s+v\d+\b",
        "Frozen Conflict Assessment Model",
    ),
    (
        r"\bConflict Ripple Propagation Engine\s+v\d+\b",
        "Conflict Ripple Propagation Model",
    ),
]

TECHNICAL_REPLACEMENTS = {
    "current_state_escalation_probability":
        "current escalation assessment",
    "historical_state_percentages":
        "historical conflict pattern",
    "historical_state_counts":
        "historical conflict record",
    "historical_year_count":
        "historical coverage",
    "canonical_episode_id":
        "historical conflict record",
    "conflict_id":
        "conflict record",
    "episode_end":
        "conflict conclusion status",
    "current_state":
        "current conflict condition",
    "observation_count":
        "current reporting volume",
    "evidence_count":
        "available evidence",
    "event_type_counts":
        "observed event pattern",
    "frozen_hazard":
        "frozen-conflict assessment",
    "preconflict":
        "early-warning assessment",
    "hawkes":
        "temporal escalation assessment",
    "dyadic":
        "interstate escalation assessment",
}

MODEL_PATTERNS = [
    r"\bconflict-state-v\d+\b",
    r"\bconflict-ensemble-v\d+\b",
    r"\bempirical-annual-markov-v\d+\b",
    r"\bpre-conflict-bayesian-logit-v\d+\b",
    r"\bdyadic-escalation-v\d+\b",
    r"\bfrozen-conflict-hazard-v\d+\b",
    r"\bhawkes-escalation-v\d+\b",
    r"\bconflict-rpe-v\d+\b",
    r"\bconflict-analysis-packet-v\d+\b",
    r"\bconflict-agent-packet-v\d+\b",
    r"\bconflict-intelligence-analyst-v\d+\b",
    r"\bconflict-agent-analyst-v\d+\b",
]

FORBIDDEN_PRESENTATION_PATTERNS = [
    r"\bconflict_id\b",
    r"\bcanonical_episode_id\b",
    r"\bcurrent_state\b",
    r"\bhistorical_state_counts\b",
    r"\bhistorical_state_percentages\b",
    r"\bcurrent_state_escalation_probability\b",
    r"\bepisode_end\b",
    r"\bfrozen_hazard\b",
    r"\bValueError\b",
    r"\bRuntimeError\b",
    r"\bKeyError\b",
    r"\bTypeError\b",
    r"\bS[0-5]_[A-Z_]+\b",
    r"\bS[0-5]\b",
]

URL_KEYS = {
    "source_url",
    "url",
    "display_url",
}


def _deep_get(
    obj: Any,
    *path: str,
) -> Any:
    current = obj

    for key in path:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


def _walk_values(
    obj: Any,
) -> list[Any]:
    values: list[Any] = []

    if isinstance(obj, dict):
        for value in obj.values():
            values.extend(
                _walk_values(value)
            )

    elif isinstance(obj, list):
        for value in obj:
            values.extend(
                _walk_values(value)
            )

    else:
        values.append(obj)

    return values


def _is_recent_timestamp(
    value: Any,
    *,
    lookback_days: int,
) -> bool:
    if not value:
        return False

    from datetime import datetime, timezone, timedelta

    text = str(value).strip()

    try:
        dt = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        return False

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=lookback_days)
    )

    return dt >= cutoff


def _record_is_usable(
    record: dict[str, Any],
) -> bool:
    if record.get("active") is False:
        return False

    review = str(
        record.get("review_status")
        or record.get("status")
        or ""
    ).strip().lower()

    if review in {
        "retracted",
        "rejected",
        "invalid",
        "inactive",
        "deleted",
    }:
        return False

    return True


def _record_timestamp(
    record: dict[str, Any],
) -> Any:
    for key in (
        "observed_at",
        "published_at",
        "event_date",
        "timestamp",
        "created_at",
        "updated_at",
    ):
        if record.get(key):
            return record.get(key)

    return None


def _record_text(
    record: dict[str, Any],
) -> str:
    return " ".join(
        str(value)
        for value in _walk_values(record)
        if isinstance(
            value,
            (str, int, float),
        )
    ).lower()


def _looks_like_active_hostilities(
    record: dict[str, Any],
) -> bool:
    text = _record_text(record)

    active_terms = (
        "war",
        "armed conflict",
        "combat",
        "hostilities",
        "military strike",
        "airstrike",
        "missile strike",
        "drone strike",
        "shelling",
        "artillery",
        "offensive",
        "invasion",
        "battle",
        "firefight",
        "troop engagement",
        "ceasefire violation",
        "territorial fighting",
    )

    return any(
        term in text
        for term in active_terms
    )


def _looks_like_emerging_risk(
    record: dict[str, Any],
) -> bool:
    text = _record_text(record)

    emerging_terms = (
        "escalation",
        "mobilization",
        "military buildup",
        "troop movement",
        "heightened tension",
        "diplomatic rupture",
        "border tension",
        "threat",
        "warning",
        "military exercise",
        "retaliation",
    )

    return any(
        term in text
        for term in emerging_terms
    )


def detect_assessment_mode(
    packet: dict[str, Any],
) -> AssessmentMode:
    """
    Deterministic precedence:

    ACTIVE
    -> EMERGING
    -> FROZEN_UNRESOLVED
    -> HISTORICAL_CONCLUDED

    Historical termination is fallback context only.
    """

    request = (
        packet.get("request")
        if isinstance(
            packet.get("request"),
            dict,
        )
        else {}
    )

    lookback_days = int(
        request.get(
            "lookback_days",
            90,
        )
        or 90
    )

    current_state = (
        _deep_get(
            packet,
            "conflict",
            "current_state",
        )
        or _deep_get(
            packet,
            "authoritative_metrics",
            "current_state",
        )
        or _deep_get(
            packet,
            "current_state",
        )
    )

    state_code = ""

    if isinstance(
        current_state,
        dict,
    ):
        state_code = str(
            current_state.get(
                "state_code"
            )
            or current_state.get(
                "state"
            )
            or ""
        ).upper()

    elif isinstance(
        current_state,
        str,
    ):
        state_code = (
            current_state.upper()
        )

    if state_code in {
        "S4_WAR",
        "S3_LIMITED_CONFLICT",
    }:
        return AssessmentMode.ACTIVE

    if state_code in {
        "S2_CRISIS",
        "S1_TENSION",
    }:
        return AssessmentMode.EMERGING

    frozen_state = (
        state_code == "S5_FROZEN"
    )

    records: list[
        dict[str, Any]
    ] = []

    for key in (
        "current_observations",
        "current_evidence",
    ):
        value = packet.get(key)

        if isinstance(value, list):
            records.extend(
                row
                for row in value
                if isinstance(
                    row,
                    dict,
                )
            )

        elif isinstance(value, dict):
            for child in value.values():
                if isinstance(
                    child,
                    list,
                ):
                    records.extend(
                        row
                        for row in child
                        if isinstance(
                            row,
                            dict,
                        )
                    )

    live_collection = packet.get(
        "live_collection"
    )

    if isinstance(
        live_collection,
        dict,
    ):
        for value in (
            live_collection.values()
        ):
            if isinstance(value, list):
                records.extend(
                    row
                    for row in value
                    if isinstance(
                        row,
                        dict,
                    )
                )

            elif isinstance(value, dict):
                for child in value.values():
                    if isinstance(
                        child,
                        list,
                    ):
                        records.extend(
                            row
                            for row in child
                            if isinstance(
                                row,
                                dict,
                            )
                        )

    recent_records = []

    for record in records:
        if not _record_is_usable(
            record
        ):
            continue

        timestamp = (
            _record_timestamp(
                record
            )
        )

        if not _is_recent_timestamp(
            timestamp,
            lookback_days=
                lookback_days,
        ):
            continue

        recent_records.append(
            record
        )

    if any(
        _looks_like_active_hostilities(
            record
        )
        for record in recent_records
    ):
        return AssessmentMode.ACTIVE

    if any(
        _looks_like_emerging_risk(
            record
        )
        for record in recent_records
    ):
        return AssessmentMode.EMERGING

    if frozen_state:
        return (
            AssessmentMode.FROZEN_UNRESOLVED
        )

    packet_text = " ".join(
        str(value)
        for value in _walk_values(
            packet
        )
        if isinstance(
            value,
            (str, int, float),
        )
    ).lower()

    if (
        "frozen conflict"
        in packet_text
        or "ceasefire-unresolved"
        in packet_text
        or "unresolved ceasefire"
        in packet_text
    ):
        return (
            AssessmentMode.FROZEN_UNRESOLVED
        )

    historical_termination = False

    episode_candidates = []

    conflict = packet.get(
        "conflict"
    )

    if isinstance(
        conflict,
        dict,
    ):
        episode_candidates.append(
            conflict
        )

        canonical = conflict.get(
            "canonical_episode"
        )

        if isinstance(
            canonical,
            dict,
        ):
            episode_candidates.append(
                canonical
            )

    baseline = packet.get(
        "baseline_conflict_data"
    )

    if isinstance(
        baseline,
        list,
    ):
        episode_candidates.extend(
            row
            for row in baseline
            if isinstance(
                row,
                dict,
            )
        )

    for episode in episode_candidates:
        if (
            episode.get(
                "episode_end"
            )
            is True
        ):
            historical_termination = True

        if (
            episode.get(
                "active"
            )
            is False
            and episode.get(
                "end_year"
            )
        ):
            historical_termination = True

    if historical_termination:
        return (
            AssessmentMode.HISTORICAL_CONCLUDED
        )

    return AssessmentMode.EMERGING


def presentation_label(
    value: str,
) -> str:
    """
    Turn machine labels into presentation English.
    """

    if not value:
        return value

    if value in STATE_LABELS:
        return STATE_LABELS[value]

    if re.fullmatch(
        r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+",
        value,
    ):
        return (
            value.replace("_", " ")
            .strip()
            .title()
        )

    return value


def _remove_exception_text(
    text: str,
) -> str:
    """
    Remove backend exception language without inventing
    a replacement quantitative claim.
    """

    exception_patterns = [
        r"(?:ValueError|RuntimeError|KeyError|TypeError|"
        r"APITimeoutError|AIGatewayError)"
        r"\s*:\s*[^.\n]+\.?",
        r"No current state found for "
        r"(?:conflict[_ ]id|conflict record)\s*\d*\.?",
    ]

    for pattern in exception_patterns:
        text = re.sub(
            pattern,
            (
                "A calibrated quantitative forecast "
                "is not available for this assessment."
            ),
            text,
            flags=re.IGNORECASE,
        )

    return text


def _remove_internal_identifiers(
    text: str,
) -> str:
    patterns = [
        r"\bconflict[_ ]id\s*[=:]?\s*\d+\b",
        r"\bConflict\s+ID\s+\d+\b",
        r"\bcanonical[_ ]episode[_ ]id\s*[=:]?\s*"
        r"[A-Za-z0-9-]+\b",
        r"\bepisode\s+ID\s+[A-Za-z0-9-]+\b",
        r"\bCOBS-[A-Z0-9]+\b",
        r"\bCEV-[A-Z0-9]+\b",
        r"\bCIR-[A-Z0-9]+\b",
    ]

    for pattern in patterns:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    return text


def _clean_markdown(
    text: str,
) -> str:
    text = text.replace("```json", "")
    text = text.replace("```", "")

    text = re.sub(
        r"(?m)^\s{0,3}#{1,6}\s*",
        "",
        text,
    )

    text = text.replace("**", "")
    text = text.replace("__", "")

    return text


def _clean_technical_language(
    text: str,
) -> str:
    for internal, public in sorted(
        TECHNICAL_REPLACEMENTS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        text = re.sub(
            rf"\b{re.escape(internal)}\b",
            public,
            text,
            flags=re.IGNORECASE,
        )

    for state, label in STATE_LABELS.items():
        text = re.sub(
            rf"\b{re.escape(state)}\b",
            label,
            text,
        )

    # Short state codes sometimes appear in generated prose even
    # after the canonical machine state has been translated.
    for state, label in SHORT_STATE_LABELS.items():
        text = re.sub(
            rf"\b{re.escape(state)}\b",
            label,
            text,
        )

    for pattern, replacement in MODEL_PRESENTATION_REPLACEMENTS:
        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE,
        )

    for pattern in MODEL_PATTERNS:
        text = re.sub(
            pattern,
            "Sovereign Intelligence AI analytical model",
            text,
            flags=re.IGNORECASE,
        )

    # Remove repeated state labels such as:
    # "High-Intensity War (High-Intensity War)".
    for label in set(STATE_LABELS.values()):
        text = re.sub(
            rf"\b({re.escape(label)})\s*"
            rf"\(\s*{re.escape(label)}\s*\)",
            r"\1",
            text,
            flags=re.IGNORECASE,
        )

    # Normalize awkward phrases produced when an internal model
    # identifier and its public replacement appear together.
    text = re.sub(
        r"\bTemporal Escalation Model\s+temporal\b",
        "Temporal Escalation Model",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\bInterstate Escalation Model\s+escalation\b",
        "Interstate Escalation Model",
        text,
        flags=re.IGNORECASE,
    )

    return text


def _clean_snake_case_tokens(
    text: str,
) -> str:
    """
    Presentation cleanup for residual machine labels embedded
    in prose. URLs are excluded before this function is called.
    """

    pattern = re.compile(
        r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b"
    )

    return pattern.sub(
        lambda match: presentation_label(
            match.group(0)
        ),
        text,
    )


def _normalize_spacing(
    text: str,
) -> str:
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r" *\n *",
        "\n",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    text = re.sub(
        r"\(\s*\)",
        "",
        text,
    )

    text = re.sub(
        r"\[\s*\]",
        "",
        text,
    )

    text = re.sub(
        r"\s+([,.;:])",
        r"\1",
        text,
    )

    text = re.sub(
        r"([,;:]){2,}",
        r"\1",
        text,
    )

    return text.strip()


def sanitize_text(
    text: str,
) -> str:
    if not text:
        return text

    text = _clean_markdown(text)
    text = _remove_exception_text(text)
    text = _remove_internal_identifiers(text)
    text = _clean_technical_language(text)
    text = _clean_snake_case_tokens(text)
    text = _normalize_spacing(text)

    return text


def _sanitize_value(
    value: Any,
    *,
    key: str | None = None,
) -> Any:
    """
    Recursively sanitize report VALUES only.
    Dictionary keys are intentionally preserved because
    the frontend depends on the API schema.
    """

    if isinstance(value, dict):
        return {
            child_key: _sanitize_value(
                child_value,
                key=child_key,
            )
            for child_key, child_value
            in value.items()
        }

    if isinstance(value, list):
        cleaned = [
            _sanitize_value(
                item,
                key=key,
            )
            for item in value
        ]

        # Empty evidence references add visual noise and carry no
        # provenance value. Remove them only from the presentation
        # payload; underlying governed evidence remains unchanged.
        if key == "evidence_refs":
            cleaned = [
                item
                for item in cleaned
                if not (
                    isinstance(item, str)
                    and not item.strip()
                )
            ]

        return cleaned

    if isinstance(value, str):
        if key in URL_KEYS:
            return value

        return sanitize_text(value)

    # Preserve numeric outputs exactly.
    return value


def _historical_mode_cleanup(
    report: dict[str, Any],
) -> dict[str, Any]:
    """
    Historical cases remain in the same API schema so the
    frontend does not need a separate backend contract.
    """

    report["current_situation"] = sanitize_text(
        report.get(
            "current_situation"
        )
        or (
            "This selection represents a concluded historical "
            "conflict episode. The assessment therefore focuses "
            "on its strategic significance, evolution, outcome, "
            "and enduring consequences rather than treating it "
            "as an active contemporary conflict."
        )
    )

    report["forecast_outlook"] = {
        "near_term":
            "Not applicable to this concluded historical episode.",
        "medium_term":
            "Not applicable to this concluded historical episode.",
        "long_term":
            "The enduring relevance lies in the episode's strategic "
            "consequences, historical lessons, and influence on "
            "subsequent regional security dynamics.",
    }

    indicators = report.get(
        "indicators_to_watch"
    )

    if (
        not indicators
        or indicators == []
    ):
        report[
            "indicators_to_watch"
        ] = [
            (
                "No active warning indicators are assigned to "
                "this concluded historical episode."
            )
        ]

    return report


def prepare_report_for_presentation(
    report: dict[str, Any],
    *,
    packet: dict[str, Any],
) -> tuple[dict[str, Any], AssessmentMode]:
    """
    Produce a presentation-safe copy.

    Internal packet and report objects supplied by upstream
    systems are not mutated.
    """

    output = copy.deepcopy(
        report
    )

    mode = detect_assessment_mode(
        packet
    )

    output = _sanitize_value(
        output
    )

    if mode == (
        AssessmentMode.HISTORICAL_CONCLUDED
    ):
        output = (
            _historical_mode_cleanup(
                output
            )
        )

    validate_presentation_report(
        output
    )

    return output, mode


def _collect_report_strings(
    value: Any,
    *,
    key: str | None = None,
) -> list[str]:
    strings: list[str] = []

    if isinstance(value, dict):
        for child_key, child_value in value.items():
            strings.extend(
                _collect_report_strings(
                    child_value,
                    key=child_key,
                )
            )

    elif isinstance(value, list):
        for item in value:
            strings.extend(
                _collect_report_strings(
                    item,
                    key=key,
                )
            )

    elif (
        isinstance(value, str)
        and key not in URL_KEYS
    ):
        strings.append(value)

    return strings


def validate_presentation_report(
    report: dict[str, Any],
) -> None:
    """
    Prevent backend implementation details from leaking into
    customer-facing analytical prose.
    """

    text = "\n".join(
        _collect_report_strings(
            report
        )
    )

    violations: list[str] = []

    for pattern in (
        FORBIDDEN_PRESENTATION_PATTERNS
        + MODEL_PATTERNS
    ):
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            violations.append(
                pattern
            )

    snake_case = re.findall(
        r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b",
        text,
    )

    if snake_case:
        violations.append(
            "snake_case:"
            + ",".join(
                sorted(
                    set(
                        snake_case
                    )
                )[:10]
            )
        )

    if violations:
        raise ValueError(
            "User-facing conflict report "
            "failed presentation validation: "
            + " | ".join(
                violations
            )
        )
