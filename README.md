# SEWS Runtime Initialization

Loads canonical indicator definitions and approved warning-to-indicator mappings into Supabase.

Endpoints:

- `GET /api/sews/admin/runtime/status`
- `POST /api/sews/admin/runtime/initialize`

Register:

```python
from app.routes.sews_runtime_initialization import router as sews_runtime_initialization_router
app.include_router(sews_runtime_initialization_router)
```

Preview body:

```json
{"dry_run": true}
```

Apply body:

```json
{"dry_run": false}
```

This does not invent observations, scores, or live evidence. It operationalizes the existing validated 1,920 framework references while consolidating duplicate `(problem_key, indicator_key)` pairs required by the database unique constraint.
