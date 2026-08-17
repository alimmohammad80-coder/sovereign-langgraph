# Conflict Intelligence Engine — Phase 1 Foundation

## Scope

This milestone creates the deterministic ontology, state model, Supabase persistence layer,
read-only registry endpoints, and test foundation. It does not generate forecasts or impact
estimates.

## Install

```bash
pip install fastapi uvicorn supabase pydantic pytest httpx
```

## Environment

```bash
export SUPABASE_URL="..."
export SUPABASE_SERVICE_ROLE_KEY="..."
```

## Migration

Run `supabase/migrations/20260804_001_conflict_intelligence_foundation.sql`
through the Supabase SQL editor or CLI.

## Router registration

Add:

```python
from app.routes.conflict_intelligence import router as conflict_intelligence_router
```

and:

```python
app.include_router(conflict_intelligence_router)
```

## Seed

Populate the versioned JSON seed files with authoritative records, then run:

```bash
PYTHONPATH=. python scripts/seed_conflict_intelligence.py
```

## Test

```bash
PYTHONPATH=. pytest -q tests/conflict_intelligence
```

## Health

```bash
curl -s http://127.0.0.1:8000/api/conflict-intelligence/health | python3 -m json.tool
```

## Current limitation

Phase 1 establishes the ontology and evidence-ready persistence contracts. It does not yet
claim calibrated conflict probabilities, frozen-conflict hazard estimates, or quantified
impact propagation.
