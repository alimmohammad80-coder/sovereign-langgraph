# SEWS FastAPI Operational Backend

This package implements the operational path:

`raw evidence → normalized evidence → validated observation → deterministic indicator state`

## Files

- `app/schemas/sews_evidence.py`
- `app/services/sews_evidence_service.py`
- `app/services/sews_observation_service.py`
- `app/services/sews_indicator_state_service.py`
- `app/routes/sews_evidence.py`
- `tests/test_sews_indicator_state_service.py`

## Dependencies

```bash
pip install fastapi pydantic supabase
```

The code targets Pydantic v2 and current `supabase-py`.

## Environment

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

Use the service-role key only on the backend. Do not expose it to Lovable or browser code.

## Register router

In `app/main.py`:

```python
from app.routes.sews_evidence import router as sews_evidence_router

app.include_router(sews_evidence_router)
```

## Endpoints

- `POST /api/sews/evidence/ingest`
- `POST /api/sews/evidence/normalize`
- `GET /api/sews/evidence`
- `POST /api/sews/observations`
- `GET /api/sews/observations`
- `POST /api/sews/indicator-state/recalculate`
- `GET /api/sews/indicator-state/{indicator_key}`
- `GET /api/sews/warning-problems/{warning_problem_key}/state`

## Important integration check

The observation service validates indicators against:

```text
sews_indicator_definitions.indicator_key
```

If your existing indicator table uses a different primary-key column, modify
`SEWSObservationService._validate_indicator()` accordingly.

## Deterministic calculation

The state engine:

1. Uses only validated observations within the configured lookback.
2. Converts contradicting observations to `1 - normalized_value`.
3. Weights observations by:
   - observation confidence
   - source reliability
   - freshness
   - evidence count
4. Calculates confidence from:
   - evidence coverage
   - source corroboration
   - source reliability
   - freshness
   - contradiction penalty
5. Assigns `ACTIVE`, `DEGRADED`, `STALE`, or `INSUFFICIENT_EVIDENCE`.
6. Stores the current state in `sews_indicator_state`.
7. Relies on the database trigger to preserve material updates in
   `sews_indicator_state_history`.

LLMs may extract candidate evidence and draft explanatory text, but they do not
calculate the state score or confidence.
