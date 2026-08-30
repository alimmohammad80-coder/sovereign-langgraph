import copy

import pytest

from app.services.conflict_intelligence.report_presentation import (
    AssessmentMode,
    detect_assessment_mode,
    prepare_report_for_presentation,
    presentation_label,
    validate_presentation_report,
)


def _base_report():
    return {
        "bluf":
            "Conflict ID 13692 is coded as S4_WAR. "
            "ValueError: No current state found for conflict_id 13692.",

        "executive_judgment":
            "The current_state is unavailable.",

        "current_situation":
            "historical_state_percentages indicate S4_WAR.",

        "key_drivers": [
            {
                "driver":
                    "military_activity",

                "assessment":
                    "territorial_control remains relevant.",

                "evidence_refs":
                    ["UCDP/PRIO Conflict ID 13692"],
            }
        ],

        "contrary_evidence":
            [],

        "historical_context":
            "episode_end=true.",

        "escalation_pathways":
            [
                "frozen_hazard unavailable"
            ],

        "forecast_outlook": {
            "near_term":
                "ValueError: No current state found for conflict_id 13692.",
            "medium_term":
                "ValueError: No current state found for conflict_id 13692.",
            "long_term":
                "ValueError: No current state found for conflict_id 13692.",
        },

        "indicators_to_watch": [
            "diplomatic_tension",
            "military_activity",
        ],

        "strategic_implications":
            "Regional consequences remain significant.",

        "confidence_assessment":
            "Historical coding is authoritative.",

        "full_analysis":
            "The conflict_id is historical. "
            "S4_WAR appears in historical_state_counts.",

        "references": [
            {
                "number": 1,
                "citation":
                    "UCDP/PRIO Armed Conflict Dataset",
                "source_name":
                    "UCDP/PRIO",
                "source_url":
                    "https://example.com/source_file?id=13692",
            }
        ],
    }


def test_historical_report_is_professional_and_internal_data_is_unchanged():
    packet = {
        "conflict": {
            "conflict_id": 13692,
            "current_state": None,
            "canonical_episode": {
                "episode_end": True,
                "end_year": 2001,
            },
        }
    }

    report = _base_report()

    original_packet = copy.deepcopy(
        packet
    )

    cleaned, mode = (
        prepare_report_for_presentation(
            report,
            packet=packet,
        )
    )

    assert mode == (
        AssessmentMode.HISTORICAL_CONCLUDED
    )

    assert packet == original_packet
    assert (
        packet["conflict"]["conflict_id"]
        == 13692
    )

    text = str(cleaned)

    forbidden = [
        "conflict_id",
        "S4_WAR",
        "current_state",
        "ValueError",
        "frozen_hazard",
        "historical_state_counts",
        "historical_state_percentages",
    ]

    for term in forbidden:
        assert term not in text

    assert (
        cleaned["key_drivers"][0]["driver"]
        == "Military Activity"
    )

    assert (
        cleaned["indicators_to_watch"][0]
        == "Diplomatic Tension"
    )

    assert (
        cleaned["references"][0]["source_url"]
        == "https://example.com/source_file?id=13692"
    )

    assert (
        "concluded historical episode"
        in cleaned[
            "forecast_outlook"
        ][
            "near_term"
        ].lower()
    )


def test_active_report_keeps_active_mode_and_translates_labels():
    packet = {
        "conflict": {
            "current_state": {
                "state_code":
                    "S4_WAR",
            },
            "canonical_episode": {
                "episode_end":
                    False,
            },
        }
    }

    report = _base_report()

    report["bluf"] = (
        "The conflict remains at S4_WAR "
        "with sustained military_activity."
    )

    cleaned, mode = (
        prepare_report_for_presentation(
            report,
            packet=packet,
        )
    )

    assert mode == (
        AssessmentMode.ACTIVE
    )

    assert "S4_WAR" not in str(
        cleaned
    )

    assert (
        "High-Intensity War"
        in cleaned["bluf"]
    )

    assert (
        "Military Activity"
        in cleaned["bluf"]
    )


def test_presentation_labels():
    assert (
        presentation_label(
            "military_activity"
        )
        == "Military Activity"
    )

    assert (
        presentation_label(
            "S4_WAR"
        )
        == "High-Intensity War"
    )


def test_validator_rejects_internal_terms():
    with pytest.raises(
        ValueError
    ):
        validate_presentation_report(
            {
                "bluf":
                    "Internal conflict_id 123 remains visible."
            }
        )
