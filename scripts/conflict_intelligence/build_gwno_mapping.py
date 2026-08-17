from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SOURCE = Path("data/raw/ucdp_prio.csv")
OUTPUT = Path("app/data/conflict_intelligence/gwno_iso3_mapping.json")

df = pd.read_csv(
    SOURCE,
    low_memory=False,
    dtype=str,
)

codes = set()

for column in [
    "gwno_a",
    "gwno_b",
    "gwno_loc",
]:

    for value in df[column].dropna():

        for item in str(value).split(","):

            item = item.strip()

            if not item:
                continue

            if item.isdigit():
                codes.add(int(item))

payload = {
    "mapping_name": "GWNO to ISO3",
    "mapping_version": "v1",
    "generated_by": "Sovereign Intelligence AI",
    "record_count": len(codes),
    "records": [
        {
            "gwno": code,
            "iso3": None,
            "status": "unmapped",
        }
        for code in sorted(codes)
    ],
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
print("GWNO MAPPING GENERATED")
print("=" * 70)
print("Unique GWNO codes:", len(codes))
print("Output:", OUTPUT)
