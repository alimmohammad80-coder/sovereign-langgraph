# SEWS Phase 5.1 — Global Intelligence Collector

Install from the `sovereign-langgraph` root:

```bash
unzip -o sews_phase5_global_intelligence_collector.zip
```

Recommended first run without NewsAPI:

```bash
set -a
source .env
set +a

PYTHONPATH=. python3 scripts/run_global_intelligence_collection.py \
  --sources GOOGLE_NEWS_RSS GDELT \
  --batch-size 2 \
  --limit-per-query 3
```

Press `Ctrl+C` to stop. Progress is saved after every completed batch. Run the
same command later to resume.

Start over with `--reset-checkpoint`.
