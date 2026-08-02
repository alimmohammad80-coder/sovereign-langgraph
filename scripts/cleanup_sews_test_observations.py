from __future__ import annotations
import os
from dotenv import load_dotenv
from supabase import create_client

PROBLEM_KEY = "WP-HORMUZ-CLOSURE"
GENERATOR_VERSION = "sews-deterministic-matcher-v1"

load_dotenv()
db = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

result = (
    db.table("sews_observations")
    .select("id")
    .eq("warning_problem_key", PROBLEM_KEY)
    .eq("generator_version", GENERATOR_VERSION)
    .range(0, 4999)
    .execute()
)
ids = [row["id"] for row in (result.data or [])]
print(f"Found {len(ids)} generated observations for {PROBLEM_KEY}.")

for start in range(0, len(ids), 250):
    chunk = ids[start:start+250]
    db.table("sews_observation_evidence_links").delete().in_(
        "observation_id", chunk
    ).execute()
    db.table("sews_observations").delete().in_(
        "id", chunk
    ).execute()

db.table("sews_indicator_state").delete().eq(
    "warning_problem_key", PROBLEM_KEY
).execute()

print("Cleanup completed.")
