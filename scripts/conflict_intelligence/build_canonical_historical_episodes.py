from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SOURCE = Path("data/processed/historical_episodes.csv")
OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "canonical_historical_episodes.json"
)

df = pd.read_csv(SOURCE, dtype=str)

for col in [
    "year",
    "intensity",
]:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce",
    )

episodes = []

for conflict_id, group in df.groupby("conflict_id"):

    group = group.sort_values("year")

    years = [
        int(y)
        for y in group["year"].dropna().tolist()
    ]

    start_year = min(years) if years else None
    end_year = max(years) if years else None

    peak_intensity = None

    if group["intensity"].notna().any():
        peak_intensity = int(
            group["intensity"].max()
        )

    states = set()

    for col in ["side_a", "side_b"]:
        for value in group[col].dropna():
            value = str(value).strip()
            if value:
                states.add(value)

    locations = sorted({
        str(v).strip()
        for v in group["location"].dropna()
        if str(v).strip()
    })

    territories = sorted({
        str(v).strip()
        for v in group["territory"].dropna()
        if str(v).strip()
    })

    first = group.iloc[0]
    last = group.iloc[-1]

    episodes.append(
        {
            "conflict_id": int(conflict_id),
            "start_year": start_year,
            "end_year": end_year,
            "duration_years": (
                end_year - start_year + 1
                if start_year is not None
                and end_year is not None
                else None
            ),
            "location": (
                locations[0]
                if len(locations) == 1
                else locations
            ),
            "region": first.get("region"),
            "state_participants": sorted(states),
            "territories": territories,
            "conflict_type": first.get("type"),
            "peak_intensity": peak_intensity,
            "start_date": first.get("start_date"),
            "episode_end": last.get("episode_end"),
            "year_count": len(group),
            "years": years,
        }
    )

payload = {
    "registry_name":
        "Canonical Historical Conflict Episodes",
    "record_count": len(episodes),
    "records": episodes,
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
print("CANONICAL HISTORICAL EPISODES")
print("=" * 70)
print("Conflict-year rows:", len(df))
print("Distinct conflicts:", len(episodes))
print("Output:", OUTPUT)

print()
print("SAMPLE")
print("=" * 70)

for row in episodes[:10]:
    print(
        row["conflict_id"],
        "|",
        row["start_year"],
        "-",
        row["end_year"],
        "| peak:",
        row["peak_intensity"],
        "|",
        row["location"],
    )
