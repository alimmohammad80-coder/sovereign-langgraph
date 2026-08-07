# SEWS Phase 6.1 — In-place expansion

This package appends 32 new warnings to the existing registry, bringing the expected total from 20 to 52.

Run:
```bash
PYTHONPATH=. python3 scripts/expand_sews_warning_registry_in_place.py
PYTHONPATH=. python3 scripts/expand_sews_warning_registry_in_place.py --apply
PYTHONPATH=. python3 scripts/validate_sews_registry_expansion.py

set -a
source .env
set +a

PYTHONPATH=. python3 scripts/sync_new_sews_warning_problems.py
PYTHONPATH=. python3 scripts/sync_new_sews_warning_problems.py --apply
```
