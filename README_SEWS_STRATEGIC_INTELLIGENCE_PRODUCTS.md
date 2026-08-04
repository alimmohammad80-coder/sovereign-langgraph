# SEWS Strategic Intelligence Product Engine

## Install

From the `sovereign-langgraph` project root:

```bash
unzip -o sews_strategic_intelligence_product_engine.zip
```

## Apply the migration

Run this file in Supabase SQL Editor:

```text
supabase/migrations/20260803_006_sews_intelligence_products.sql
```

Or, if Supabase CLI is linked:

```bash
supabase db push
```

## Generate products

```bash
set -a
source .env
set +a

PYTHONPATH=. python3 \
scripts/generate_all_sews_intelligence_products.py
```

## Verify

```bash
python3 - <<'PY'
from app.routes.sews_evidence import get_sews_supabase_client

db = get_sews_supabase_client()
result = (
    db.table("sews_intelligence_products")
    .select("id", count="exact")
    .limit(1)
    .execute()
)
print("Strategic intelligence products:", result.count)
PY
```

## Inspect latest products

```bash
python3 - <<'PY'
from pprint import pprint
from app.routes.sews_evidence import get_sews_supabase_client

db = get_sews_supabase_client()
rows = (
    db.table("sews_latest_intelligence_products")
    .select("warning_problem_key,probability,confidence,trend,bluf,generated_at")
    .order("warning_problem_key")
    .execute()
    .data
    or []
)
pprint(rows)
PY
```
