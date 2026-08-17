from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SOURCE = Path("data/raw/ucdp_prio.csv")
OUTPUT = Path("app/data/conflict_intelligence/gwno_country_crosswalk.json")

df = pd.read_csv(
    SOURCE,
    dtype=str,
    low_memory=False,
)

rows = {}

for _, row in df.iterrows():

    for gwno_col, side_col in [
        ("gwno_a", "side_a"),
        ("gwno_b", "side_b"),
    ]:

        gwno = row.get(gwno_col)

        side = row.get(side_col)

        if pd.isna(gwno):
            continue

        for code in str(gwno).split(","):

            code = code.strip()

            if not code.isdigit():
                continue

            rows.setdefault(
                int(code),
                set(),
            ).add(str(side).strip())

payload = {
    "mapping_name": "GWNO Country Crosswalk",
    "record_count": len(rows),
    "records": [],
}

for gwno in sorted(rows):

    payload["records"].append(
        {
            "gwno": gwno,
            "candidate_names": sorted(rows[gwno]),
            "iso3": None,
        }
    )

OUTPUT.write_text(
    json.dumps(
        payload,
        indent=2,
    )
)

print("=" * 70)
print("GWNO CROSSWALK GENERATED")
print("=" * 70)
print("Unique GWNO:", len(rows))
print("Output:", OUTPUT)
