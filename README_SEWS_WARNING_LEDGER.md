# SEWS State Transitions and Immutable Warning Ledger

This package adds the next main SEWS capability:

`deterministic assessment → governed state transition → versioned warning product`

## Files

- `app/schemas/sews_warning_ledger.py`
- `app/services/sews_warning_ledger_service.py`
- `app/routes/sews_warning_ledger.py`
- `tests/test_sews_warning_ledger.py`

## Register router

```python
from app.routes.sews_warning_ledger import (
    router as sews_warning_ledger_router,
)

app.include_router(sews_warning_ledger_router)
```

## Endpoints

```text
POST /api/sews/warning-problems/{problem_key}/transition
POST /api/sews/warning-problems/{problem_key}/ledger
GET  /api/sews/warning-problems/{problem_key}/ledger
GET  /api/sews/warning-problems/{problem_key}/transitions
```

## Governance

Automated transitions are limited to one ladder step in either direction:

```text
DORMANT ↔ WATCH ↔ ADVISORY ↔ WARNING ↔ CRITICAL
```

Resolution and falsification are permitted from any active state. Reopening a
resolved/falsified problem or jumping multiple levels requires `force=true`,
which should only be used after explicit analyst adjudication.

## Ledger behavior

- One ledger entry per assessment.
- Versions increase monotonically per warning problem.
- Repeating a request for the same assessment returns the existing entry.
- Deterministic headers are generated from the assessment.
- Narrative bodies are optional and are never used to alter numeric results.
