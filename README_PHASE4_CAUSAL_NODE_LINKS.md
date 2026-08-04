# SEWS Phase 4 Causal Node Indicator Link Generator

From the sovereign-langgraph project root:

```bash
unzip -o sews_phase4_causal_node_indicator_link_generator_full.zip
```

Run:

```bash
set -a
source .env
set +a

PYTHONPATH=. python3 scripts/generate_sews_causal_node_indicator_links.py
```

Validate:

```bash
python3 - <<'PY'
from app.routes.sews_evidence import get_sews_supabase_client

db = get_sews_supabase_client()
result = (
    db.table("sews_causal_node_indicator_links")
    .select("node_id", count="exact")
    .limit(1)
    .execute()
)
print("Causal node indicator links:", result.count)
PY
```
