# SEWS Phase 5.2 — Incremental Evidence Processing

This package processes only evidence collected after the previous successful
checkpoint.

## Install

From the `sovereign-langgraph` root:

```bash
unzip -o sews_phase5_incremental_evidence_pipeline.zip
```

## First run

```bash
set -a
source .env
set +a

PYTHONPATH=. python3 scripts/run_incremental_sews_evidence_pipeline.py
```

The first run processes all currently available raw evidence. Future runs
process only newer records.

## Start the checkpoint from the current database state

To avoid processing the entire historical evidence table, run once after
placing the collector checkpoint timestamp into the incremental checkpoint, or
use the normal first run and allow it to establish the checkpoint.

## Reset

```bash
PYTHONPATH=. python3 scripts/run_incremental_sews_evidence_pipeline.py \
  --reset-checkpoint
```

## What it updates

- Detects newly collected `sews_raw_evidence`
- Identifies affected warning problems from evidence metadata
- Recalculates only their mapped indicator states
- Re-runs only their causal assessments
- Advances the checkpoint only after successful processing

It does not invent evidence or confidence.
