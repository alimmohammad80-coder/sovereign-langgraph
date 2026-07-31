# Strategic Intelligence Product Engine

This is the SEWS publication layer.

It consumes:

- official deterministic assessment
- independent AI strategic review
- indicator contribution tree
- confidence breakdown
- warning-problem context

It produces:

- BLUF, maximum seven sentences
- executive summary
- official assessment panel
- AI strategic review panel
- deterministic drivers
- contrary evidence
- confidence and provenance panel
- historical analogs
- monitoring priorities
- forecast
- approximately 500-word full analysis
- quality-assurance result
- optional warning-ledger publication

## Register the router

```python
from app.routes.strategic_intelligence_products import (
    router as strategic_intelligence_products_router,
)

app.include_router(strategic_intelligence_products_router)
```

## Run migration

Apply:

```text
supabase/migrations/20260731_006_strategic_intelligence_products.sql
```

## Tests

```bash
PYTHONPATH=. pytest \
tests/test_strategic_intelligence_product.py \
-v
```

## Endpoints

```text
POST /api/sews/warning-problems/{problem_key}/product
GET  /api/sews/warning-problems/{problem_key}/products
```

## Generation request

```json
{
  "assessment_id": "ASSESSMENT_UUID",
  "ai_review_id": "AI_REVIEW_UUID",
  "product_type": "SEWS_WARNING",
  "audience": "EXECUTIVE",
  "publish_to_ledger": true,
  "publish_product": false
}
```

The AI Gateway writes the narrative sections. Official probability, confidence,
severity, state, formula version, and deterministic indicator contributions are
copied from the assessment and cannot be rewritten by the model.
