# SEWS Phase 4 Global Causal Propagation Runner

From the `sovereign-langgraph` project root:

```bash
unzip -o sews_phase4_global_causal_propagation_runner.zip
```

Run:

```bash
set -a
source .env
set +a

PYTHONPATH=. python3 scripts/run_all_sews_causal_propagation.py
```

The runner processes all active warning problems and persists fresh
`sews_causal_assessments` rows with outcome probabilities and confidence scores.
