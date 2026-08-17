from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "historical_episodes_seed.json"
)


def validate_record(record: dict) -> None:
    required = {
        "episode_id",
        "name",
        "conflict_category",
        "start_date",
        "ongoing",
        "source",
        "review_status",
    }

    missing = required - record.keys()

    if missing:
        raise ValueError(
            f"{record.get('episode_id')}: "
            f"missing {sorted(missing)}"
        )

    if (
        not record["ongoing"]
        and not record.get("end_date")
    ):
        raise ValueError(
            f"{record['episode_id']}: "
            "completed episode requires end_date"
        )

    for field in [
        "state_participants",
        "non_state_organizations",
        "governing_authorities",
        "territory_refs",
        "dispute_refs",
        "border_dyad_refs",
        "maritime_dyad_refs",
        "frozen_conflict_refs",
    ]:
        if not isinstance(
            record.get(field, []),
            list,
        ):
            raise ValueError(
                f"{record['episode_id']}: "
                f"{field} must be list"
            )


def main() -> None:
    today = datetime.now(timezone.utc).date().isoformat()

    records: list[dict] = [
        {
            "episode_id": "EP-KOREAN-WAR-1950",
            "name": "Korean War",
            "short_name": "Korean War",
            "conflict_category": "interstate",
            "conflict_subtype": "internationalized interstate war",
            "start_date": "1950-06-25",
            "end_date": "1953-07-27",
            "ongoing": False,

            "state_participants": [
                "PRK",
                "KOR",
                "CHN",
                "USA",
            ],
            "non_state_organizations": [],
            "governing_authorities": [],

            "territory_refs": [],
            "dispute_refs": [],
            "border_dyad_refs": [],
            "maritime_dyad_refs": [],
            "frozen_conflict_refs": [],

            "initial_trigger": "cross-border invasion",
            "primary_escalation_driver": "large-scale interstate military intervention",

            "initial_state": None,
            "peak_state": "S4_WAR",
            "terminal_state": "S5_FROZEN",

            "termination_type": "armistice",
            "deescalation_method": "armistice",

            "battle_deaths_low": None,
            "battle_deaths_high": None,
            "civilian_deaths": None,
            "refugees": None,
            "internally_displaced": None,

            "economic_damage_estimate": None,
            "economic_damage_currency": None,
            "economic_damage_year": None,

            "air_campaign": True,
            "naval_campaign": True,
            "occupation_occurred": True,
            "foreign_intervention": True,
            "peacekeeping_present": False,

            "territorial_change": False,
            "government_change": False,
            "new_state_created": False,
            "annexation_occurred": False,
            "demilitarized_zone_created": True,
            "sanctions_imposed": False,
            "peace_agreement_signed": False,

            "trigger_summary": (
                "Large-scale armed conflict began with North Korean "
                "forces crossing the 38th parallel into South Korea."
            ),
            "outcome_summary": (
                "Large-scale hostilities ended under an armistice, "
                "leaving the Korean Peninsula divided."
            ),

            "strategic_lessons": [],
            "warning_indicators": [],
            "leading_indicators": [],
            "lagging_indicators": [],
            "historical_similarity_vector": None,

            "external_ids": {
                "ucdp_dataset": "UCDP/PRIO Armed Conflict Dataset v26.1"
            },

            "source": "Uppsala Conflict Data Program",
            "source_url": "https://ucdp.uu.se/downloads/",
            "source_version": "26.1",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
            "active": True,
        },

        {
            "episode_id": "EP-GULF-WAR-1990",
            "name": "Gulf War",
            "short_name": "Gulf War",
            "conflict_category": "interstate",
            "conflict_subtype": "interstate invasion and multinational intervention",
            "start_date": "1990-08-02",
            "end_date": "1991-02-28",
            "ongoing": False,

            "state_participants": [
                "IRQ",
                "KWT",
                "USA",
                "GBR",
                "SAU",
            ],
            "non_state_organizations": [],
            "governing_authorities": [],

            "territory_refs": [],
            "dispute_refs": [],
            "border_dyad_refs": [],
            "maritime_dyad_refs": [],
            "frozen_conflict_refs": [],

            "initial_trigger": "invasion",
            "primary_escalation_driver": "occupation and multinational military intervention",

            "initial_state": None,
            "peak_state": "S4_WAR",
            "terminal_state": "S1_TENSION",

            "termination_type": "military_victory",
            "deescalation_method": "cessation of major combat operations",

            "battle_deaths_low": None,
            "battle_deaths_high": None,
            "civilian_deaths": None,
            "refugees": None,
            "internally_displaced": None,

            "economic_damage_estimate": None,
            "economic_damage_currency": None,
            "economic_damage_year": None,

            "air_campaign": True,
            "naval_campaign": True,
            "occupation_occurred": True,
            "foreign_intervention": True,
            "peacekeeping_present": False,

            "territorial_change": False,
            "government_change": False,
            "new_state_created": False,
            "annexation_occurred": False,
            "demilitarized_zone_created": False,
            "sanctions_imposed": True,
            "peace_agreement_signed": False,

            "trigger_summary": (
                "The episode began with Iraq's invasion and occupation "
                "of Kuwait."
            ),
            "outcome_summary": (
                "Coalition forces expelled Iraqi forces from Kuwait "
                "and major combat operations ceased."
            ),

            "strategic_lessons": [],
            "warning_indicators": [],
            "leading_indicators": [],
            "lagging_indicators": [],
            "historical_similarity_vector": None,

            "external_ids": {
                "ucdp_dataset": "UCDP/PRIO Armed Conflict Dataset v26.1"
            },

            "source": "Uppsala Conflict Data Program",
            "source_url": "https://ucdp.uu.se/downloads/",
            "source_version": "26.1",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
            "active": True,
        },

        {
            "episode_id": "EP-KARGIL-1999",
            "name": "Kargil Conflict",
            "short_name": "Kargil",
            "conflict_category": "border_conflict",
            "conflict_subtype": "limited interstate conflict",
            "start_date": "1999-05-03",
            "end_date": "1999-07-26",
            "ongoing": False,

            "state_participants": [
                "IND",
                "PAK",
            ],
            "non_state_organizations": [],
            "governing_authorities": [],

            "territory_refs": [
                "TERRITORY-KASHMIR"
            ],
            "dispute_refs": [
                "DISPUTE-IND-PAK-KASHMIR"
            ],
            "border_dyad_refs": [
                "DYAD-IND-PAK-LAND"
            ],
            "maritime_dyad_refs": [],
            "frozen_conflict_refs": [
                "FC-IND-PAK-KASHMIR"
            ],

            "initial_trigger": "cross-line infiltration and military confrontation",
            "primary_escalation_driver": "contested territorial control",

            "initial_state": "S2_CRISIS",
            "peak_state": "S3_LIMITED_CONFLICT",
            "terminal_state": "S1_TENSION",

            "termination_type": "withdrawal",
            "deescalation_method": "military withdrawal and diplomatic pressure",

            "battle_deaths_low": None,
            "battle_deaths_high": None,
            "civilian_deaths": None,
            "refugees": None,
            "internally_displaced": None,

            "economic_damage_estimate": None,
            "economic_damage_currency": None,
            "economic_damage_year": None,

            "air_campaign": True,
            "naval_campaign": False,
            "occupation_occurred": False,
            "foreign_intervention": False,
            "peacekeeping_present": False,

            "territorial_change": False,
            "government_change": False,
            "new_state_created": False,
            "annexation_occurred": False,
            "demilitarized_zone_created": False,
            "sanctions_imposed": False,
            "peace_agreement_signed": False,

            "trigger_summary": (
                "Fighting escalated after incursions and military "
                "positions were detected in the Kargil sector."
            ),
            "outcome_summary": (
                "The episode ended following withdrawal from contested "
                "positions and de-escalation."
            ),

            "strategic_lessons": [],
            "warning_indicators": [],
            "leading_indicators": [],
            "lagging_indicators": [],
            "historical_similarity_vector": None,

            "external_ids": {
                "ucdp_dataset": "UCDP/PRIO Armed Conflict Dataset v26.1"
            },

            "source": "Uppsala Conflict Data Program",
            "source_url": "https://ucdp.uu.se/downloads/",
            "source_version": "26.1",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
            "active": True,
        },

        {
            "episode_id": "EP-GEORGIA-2008",
            "name": "Russia–Georgia War",
            "short_name": "Georgia 2008",
            "conflict_category": "internationalized_intrastate",
            "conflict_subtype": "interstate intervention around separatist territories",
            "start_date": "2008-08-07",
            "end_date": "2008-08-16",
            "ongoing": False,

            "state_participants": [
                "GEO",
                "RUS",
            ],
            "non_state_organizations": [],
            "governing_authorities": [],

            "territory_refs": [],
            "dispute_refs": [],
            "border_dyad_refs": [
                "DYAD-GEO-RUS-LAND"
            ],
            "maritime_dyad_refs": [],
            "frozen_conflict_refs": [],

            "initial_trigger": "rapid escalation around contested territory",
            "primary_escalation_driver": "military intervention",

            "initial_state": "S2_CRISIS",
            "peak_state": "S4_WAR",
            "terminal_state": "S1_TENSION",

            "termination_type": "ceasefire",
            "deescalation_method": "internationally mediated ceasefire",

            "battle_deaths_low": None,
            "battle_deaths_high": None,
            "civilian_deaths": None,
            "refugees": None,
            "internally_displaced": None,

            "economic_damage_estimate": None,
            "economic_damage_currency": None,
            "economic_damage_year": None,

            "air_campaign": True,
            "naval_campaign": True,
            "occupation_occurred": True,
            "foreign_intervention": True,
            "peacekeeping_present": True,

            "territorial_change": True,
            "government_change": False,
            "new_state_created": False,
            "annexation_occurred": False,
            "demilitarized_zone_created": False,
            "sanctions_imposed": False,
            "peace_agreement_signed": False,

            "trigger_summary": (
                "Escalation around South Ossetia developed into direct "
                "warfare between Georgian and Russian forces."
            ),
            "outcome_summary": (
                "Large-scale combat ended following an internationally "
                "mediated ceasefire."
            ),

            "strategic_lessons": [],
            "warning_indicators": [],
            "leading_indicators": [],
            "lagging_indicators": [],
            "historical_similarity_vector": None,

            "external_ids": {
                "ucdp_dataset": "UCDP/PRIO Armed Conflict Dataset v26.1"
            },

            "source": "Uppsala Conflict Data Program",
            "source_url": "https://ucdp.uu.se/downloads/",
            "source_version": "26.1",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
            "active": True,
        },

        {
            "episode_id": "EP-NAGORNO-KARABAKH-2020",
            "name": "Second Nagorno-Karabakh War",
            "short_name": "Nagorno-Karabakh 2020",
            "conflict_category": "interstate",
            "conflict_subtype": "territorial war",
            "start_date": "2020-09-27",
            "end_date": "2020-11-10",
            "ongoing": False,

            "state_participants": [
                "ARM",
                "AZE",
            ],
            "non_state_organizations": [],
            "governing_authorities": [],

            "territory_refs": [],
            "dispute_refs": [],
            "border_dyad_refs": [
                "DYAD-ARM-AZE-LAND"
            ],
            "maritime_dyad_refs": [],
            "frozen_conflict_refs": [],

            "initial_trigger": "renewed large-scale fighting",
            "primary_escalation_driver": "unresolved territorial dispute and military escalation",

            "initial_state": "S2_CRISIS",
            "peak_state": "S4_WAR",
            "terminal_state": "S5_FROZEN",

            "termination_type": "ceasefire",
            "deescalation_method": "Russia-brokered ceasefire",

            "battle_deaths_low": None,
            "battle_deaths_high": None,
            "civilian_deaths": None,
            "refugees": None,
            "internally_displaced": None,

            "economic_damage_estimate": None,
            "economic_damage_currency": None,
            "economic_damage_year": None,

            "air_campaign": True,
            "naval_campaign": False,
            "occupation_occurred": True,
            "foreign_intervention": False,
            "peacekeeping_present": True,

            "territorial_change": True,
            "government_change": False,
            "new_state_created": False,
            "annexation_occurred": False,
            "demilitarized_zone_created": False,
            "sanctions_imposed": False,
            "peace_agreement_signed": False,

            "trigger_summary": (
                "Sustained fighting resumed along the Nagorno-Karabakh "
                "line of contact and rapidly escalated."
            ),
            "outcome_summary": (
                "The war ended with a ceasefire and major changes in "
                "territorial control."
            ),

            "strategic_lessons": [],
            "warning_indicators": [],
            "leading_indicators": [],
            "lagging_indicators": [],
            "historical_similarity_vector": None,

            "external_ids": {
                "ucdp_dataset": "UCDP/PRIO Armed Conflict Dataset v26.1"
            },

            "source": "Uppsala Conflict Data Program",
            "source_url": "https://ucdp.uu.se/downloads/",
            "source_version": "26.1",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
            "active": True,
        },
    ]

    for record in records:
        validate_record(record)

    ids = [
        record["episode_id"]
        for record in records
    ]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate episode_id detected"
        )

    payload = {
        "registry_name":
            "Conflict Intelligence "
            "Historical Episodes",

        "registry_version":
            "conflict-historical-episodes-v1",

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "record_count":
            len(records),

        "records":
            records,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
        )
    )

    print(
        f"Created {OUTPUT}"
    )

    print(
        f"Records: {len(records)}"
    )

    print(
        "Historical episode registry "
        "structure ready."
    )


if __name__ == "__main__":
    main()
