# SEWS Phase 5.3 — Scheduled Intelligence Workflow

This package connects the validated Phase 5 components:

1. Global intelligence collection
2. Incremental evidence detection
3. Affected indicator-state recalculation
4. Affected causal-assessment updates

## Install

From the `sovereign-langgraph` project root:

```bash
unzip -o sews_phase5_scheduled_intelligence_workflow.zip
```

## Test one cycle

```bash
set -a
source .env
set +a

PYTHONPATH=. python3 \
scripts/run_scheduled_sews_workflow.py \
--mode once \
--sources GOOGLE_NEWS_RSS GDELT \
--batch-size 2 \
--limit-per-query 3
```

Because the global collection checkpoint already contains all 20 warnings,
the first test may collect nothing. To begin a new collection cycle, reset only
the collection checkpoint:

```bash
PYTHONPATH=. python3 \
scripts/run_scheduled_sews_workflow.py \
--mode once \
--sources GOOGLE_NEWS_RSS GDELT \
--batch-size 2 \
--limit-per-query 3 \
--reset-collection-checkpoint
```

Do not reset the incremental checkpoint during normal cycles. It ensures only
newly persisted evidence is processed downstream.

## Run continuously every 60 minutes

```bash
PYTHONPATH=. python3 \
scripts/run_scheduled_sews_workflow.py \
--mode forever \
--interval-minutes 60 \
--sources GOOGLE_NEWS_RSS GDELT \
--batch-size 2 \
--limit-per-query 3
```

Stop with `Ctrl+C`.

## Run every 30 minutes

```bash
PYTHONPATH=. python3 \
scripts/run_scheduled_sews_workflow.py \
--mode forever \
--interval-minutes 30 \
--sources GOOGLE_NEWS_RSS GDELT \
--batch-size 2 \
--limit-per-query 3
```

## Lock recovery

The workflow prevents overlapping cycles. If the process is killed and leaves
a stale lock:

```bash
PYTHONPATH=. python3 \
scripts/run_scheduled_sews_workflow.py \
--mode once \
--clear-stale-lock
```

## Important behavior

- The collection checkpoint makes interrupted batches resumable.
- The incremental checkpoint prevents unnecessary recalculation.
- A workflow state file records the latest cycle.
- Causal propagation runs only for warnings affected by new evidence.
- Missing evidence remains `INSUFFICIENT_EVIDENCE`; no confidence is invented.
