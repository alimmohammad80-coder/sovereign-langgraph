from __future__ import annotations

from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_strategic_intelligence_production_service import (
    SEWSStrategicIntelligenceProductionService,
)


def main() -> None:
    db = get_sews_supabase_client()
    problems = (
        db.table("sews_warning_problems")
        .select("problem_key")
        .eq("active", True)
        .order("problem_key")
        .range(0, 4999)
        .execute()
        .data
        or []
    )
    service = SEWSStrategicIntelligenceProductionService(db)
    results, errors = [], []
    for index, row in enumerate(problems, 1):
        key = row["problem_key"]
        try:
            product = service.generate(key, persist=True)
            results.append({
                "problem_key": key,
                "product_id": product.get("id"),
                "probability": product.get("probability"),
                "confidence": product.get("confidence"),
                "trend": product.get("trend"),
            })
            print(f"[{index}/{len(problems)}] ✅ {key} | p={product['probability']:.4f} confidence={product['confidence']:.2f}")
        except Exception as exc:
            errors.append({"problem_key": key, "error": f"{type(exc).__name__}: {exc}"})
            print(f"[{index}/{len(problems)}] ❌ {key} | {type(exc).__name__}: {exc}")
    print("\n" + "=" * 80)
    print("SEWS STRATEGIC INTELLIGENCE PRODUCT SUMMARY")
    print("=" * 80)
    pprint({
        "warning_problems_processed": len(problems),
        "products_generated": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    })


if __name__ == "__main__":
    main()
