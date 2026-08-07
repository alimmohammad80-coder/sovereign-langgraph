# SEWS Phase 6.4 — Cross-Warning Dependency Expansion

This package adds a curated set of 75 deterministic cross-warning relationships to the existing `sews_warning_dependencies` table.

It preserves all existing relationships and skips exact source-target-type duplicates.

## Run

```bash
cp ~/Downloads/sews_phase6_4_dependency_expansion.zip .
unzip -o sews_phase6_4_dependency_expansion.zip

set -a
source .env
set +a

PYTHONPATH=. python3 scripts/sync_sews_cross_warning_dependency_expansion.py
PYTHONPATH=. python3 scripts/sync_sews_cross_warning_dependency_expansion.py --apply
PYTHONPATH=. python3 scripts/validate_sews_dependency_network_coverage.py
```

After validation, run the existing validator and propagation workflows.
