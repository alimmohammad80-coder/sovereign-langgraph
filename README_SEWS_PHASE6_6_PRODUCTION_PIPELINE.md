# SEWS Phase 6.6 — Unified Production Pipeline

This package adds one auditable production entry point while reusing the
existing collection, incremental evidence, causal propagation, and strategic
product runners.

It does not replace the existing analytical services.

## Install

```bash
cp ~/Downloads/sews_phase6_6_production_pipeline.zip .
unzip -o sews_phase6_6_production_pipeline.zip
```

## Apply migration

Run `supabase/migrations/20260806_001_sews_pipeline_runs.sql` in Supabase SQL Editor.

## Compile

```bash
PYTHONPATH=. python3 -m py_compile \
app/services/sews_pipeline_orchestrator.py \
scripts/run_sews_production_pipeline.py \
scripts/validate_sews_dependencies_read_only.py
```

## Validate dependency contracts safely

This validator is read-only and preserves curated dependency types.

```bash
set -a
source .env
set +a

PYTHONPATH=. python3 scripts/validate_sews_dependencies_read_only.py
```

## Run one complete production cycle

```bash
PYTHONPATH=. python3 scripts/run_sews_production_pipeline.py \
--mode once \
--sources GOOGLE_NEWS_RSS GDELT \
--batch-size 2 \
--limit-per-query 3
```

## Run continuously every 60 minutes

Stop the older forever-mode process first, then run:

```bash
PYTHONPATH=. python3 scripts/run_sews_production_pipeline.py \
--mode forever \
--interval-minutes 60 \
--sources GOOGLE_NEWS_RSS GDELT \
--batch-size 2 \
--limit-per-query 3
```

The collection checkpoint resets at the start of every cycle. The incremental
evidence checkpoint remains preserved by the existing workflow.

## Verify run ledger

```bash
python3 - <<'PY'
from pprint import pprint
from app.routes.sews_evidence import get_sews_supabase_client

db = get_sews_supabase_client()
rows = (
    db.table("sews_pipeline_runs")
    .select(
        "run_key,status,started_at,finished_at,duration_seconds,"
        "warnings_updated,indicators_updated,evidence_records,"
        "propagation_events,products_generated,errors"
    )
    .order("started_at", desc=True)
    .limit(5)
    .execute()
    .data
    or []
)
pprint(rows)
PY
```

## Important

Do not run the old mutating dependency validator. Use
`scripts/validate_sews_dependencies_read_only.py`.
