# SEWS Warning Scoring Backend

This package adds the main deterministic SEWS warning assessment layer.

## Install

Extract into the repository root, then register:

```python
from app.routes.sews_warning_scoring import router as sews_warning_scoring_router
app.include_router(sews_warning_scoring_router)
```

## Test

```bash
PYTHONPATH=. pytest tests/test_sews_warning_scoring.py -v
```

## Endpoint

```text
POST /api/sews/warning-problems/{problem_key}/assess
```

Example body:

```json
{
  "country_iso3": "IRN",
  "region_key": "MIDDLE_EAST",
  "minimum_indicator_confidence": 30,
  "minimum_indicator_count": 2,
  "persist": true
}
```
