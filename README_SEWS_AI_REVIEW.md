# SEWS AI Strategic Review

This layer provides an independent AI second opinion without modifying the
official deterministic SEWS assessment.

## Architecture

```text
Official deterministic assessment
        ↓
Independent AI strategic review
        ↓
Variance and agreement calculation
        ↓
Analyst-review flag when divergence is material
```

## Register router

```python
from app.routes.sews_ai_review import (
    router as sews_ai_review_router,
)

app.include_router(sews_ai_review_router)
```

## Environment

For NVIDIA/Nemotron:

```text
NVIDIA_API_KEY=...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NEMOTRON_MODEL=...
```

For OpenAI:

```text
OPENAI_API_KEY=...
OPENAI_REVIEW_MODEL=...
```

## Endpoints

```text
POST /api/sews/warning-problems/{problem_key}/ai-review

GET /api/sews/warning-problems/{problem_key}/assessment-comparison
    ?assessment_id=<uuid>
    &review_id=<uuid>
```

## Divergence rules

```text
≤ 5 percentage points   AGREE
> 5–10 points           MINOR_DISAGREEMENT
> 10–20 points          MAJOR_DISAGREEMENT
> 20 points             CRITICAL_DIVERGENCE
```

Major and critical divergence require analyst review. The AI output never
rewrites the official assessment, transition history, or ledger record.
