import json
from pathlib import Path

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_causal_propagation_service import (
    SEWSCausalPropagationService,
)

db = get_sews_supabase_client()
service = SEWSCausalPropagationService(db)

registry = json.loads(
    Path(
        "app/data/sews_global_warning_registry.json"
    ).read_text()
)

success = 0
failed = 0

for problem in registry["warning_problems"]:
    if not problem.get("active", True):
        continue

    key = problem["problem_key"]

    try:
        result = service.propagate(
            key,
            persist=True,
        )
        success += 1
        print(
            f"✅ {key}: "
            f"{result['outcome_probability']:.4f} "
            f"confidence={result['confidence_score']:.2f}"
        )
    except Exception as exc:
        failed += 1
        print(
            f"❌ {key}: "
            f"{type(exc).__name__}: {exc}"
        )

print(f"\nSuccess: {success} | Failed: {failed}")
