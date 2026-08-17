from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


SOURCE = Path(
    "data/processed/"
    "conflict_state_timeline.csv"
)

OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "state_transition_matrix.json"
)

MATRIX_VERSION = (
    "conflict-transition-matrix-v1"
)


df = pd.read_csv(
    SOURCE,
    dtype=str,
)

df["conflict_id"] = pd.to_numeric(
    df["conflict_id"],
    errors="coerce",
).astype("Int64")

df["year"] = pd.to_numeric(
    df["year"],
    errors="coerce",
).astype("Int64")

df = df.dropna(
    subset=[
        "conflict_id",
        "year",
        "state_code",
    ]
)

df = df.sort_values(
    [
        "conflict_id",
        "year",
    ]
)


transition_counts = Counter()

from_totals = Counter()

transition_conflicts = defaultdict(
    set
)

total_transitions = 0


for conflict_id, group in df.groupby(
    "conflict_id"
):

    group = group.sort_values(
        "year"
    ).reset_index(
        drop=True
    )

    for i in range(
        len(group) - 1
    ):

        current = group.iloc[i]
        following = group.iloc[i + 1]

        current_year = int(
            current["year"]
        )

        next_year = int(
            following["year"]
        )

        # Only model real consecutive-year transitions.
        if next_year != current_year + 1:
            continue

        from_state = str(
            current["state_code"]
        )

        to_state = str(
            following["state_code"]
        )

        key = (
            from_state,
            to_state,
        )

        transition_counts[key] += 1

        from_totals[
            from_state
        ] += 1

        transition_conflicts[
            key
        ].add(
            int(conflict_id)
        )

        total_transitions += 1


records = []

for (
    from_state,
    to_state,
), count in sorted(
    transition_counts.items()
):

    denominator = (
        from_totals[
            from_state
        ]
    )

    probability = (
        count / denominator
        if denominator
        else 0.0
    )

    records.append(
        {
            "matrix_version":
                MATRIX_VERSION,

            "from_state":
                from_state,

            "to_state":
                to_state,

            "transition_count":
                count,

            "from_state_total":
                denominator,

            "probability":
                round(
                    probability,
                    6,
                ),

            "conflict_count":
                len(
                    transition_conflicts[
                        (
                            from_state,
                            to_state,
                        )
                    ]
                ),

            "source":
                "UCDP/PRIO",

            "source_version":
                "26.1",

            "generated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "active":
                True,

            "review_status":
                "validated",
        }
    )


payload = {
    "matrix_name":
        "Historical Conflict State Transition Matrix",

    "matrix_version":
        MATRIX_VERSION,

    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "timeline_rows":
        len(df),

    "conflicts":
        int(
            df[
                "conflict_id"
            ].nunique()
        ),

    "total_transitions":
        total_transitions,

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


print("=" * 70)
print("HISTORICAL TRANSITION MATRIX")
print("=" * 70)

print(
    "Timeline rows:",
    len(df),
)

print(
    "Conflicts:",
    df["conflict_id"].nunique(),
)

print(
    "Transitions:",
    total_transitions,
)

print(
    "Matrix cells:",
    len(records),
)

print()

for record in records:

    print(
        record["from_state"],
        "->",
        record["to_state"],
        "| count:",
        record["transition_count"],
        "| p:",
        record["probability"],
        "| conflicts:",
        record["conflict_count"],
    )

print()
print(
    "Output:",
    OUTPUT,
)
