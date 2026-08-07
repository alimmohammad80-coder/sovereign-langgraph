from __future__ import annotations

import argparse
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_strategic_intelligence_production_service import (
    SEWSStrategicIntelligenceProductionService,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate SEWS intelligence products for all active warnings "
            "or only selected warning problem keys."
        )
    )
    parser.add_argument(
        "--problem-keys",
        nargs="+",
        default=None,
        help=(
            "Optional warning problem keys. "
            "When omitted, all active warnings are processed."
        ),
    )
    return parser.parse_args()


def load_problem_keys(
    db,
    requested_keys: list[str] | None,
) -> list[str]:
    query = (
        db.table("sews_warning_problems")
        .select("problem_key")
        .eq("active", True)
        .order("problem_key")
    )

    if requested_keys:
        normalized = sorted(
            {
                str(key).strip()
                for key in requested_keys
                if str(key).strip()
            }
        )

        if not normalized:
            return []

        rows = (
            query
            .in_("problem_key", normalized)
            .range(0, 4999)
            .execute()
            .data
            or []
        )

        found = {
            row["problem_key"]
            for row in rows
        }
        missing = sorted(set(normalized) - found)

        if missing:
            raise SystemExit(
                "Unknown or inactive warning problem keys: "
                + ", ".join(missing)
            )

        return [
            row["problem_key"]
            for row in rows
        ]

    rows = (
        query
        .range(0, 4999)
        .execute()
        .data
        or []
    )

    return [
        row["problem_key"]
        for row in rows
    ]


def main() -> None:
    args = parse_args()
    db = get_sews_supabase_client()

    problem_keys = load_problem_keys(
        db,
        args.problem_keys,
    )

    service = SEWSStrategicIntelligenceProductionService(db)

    results = []
    errors = []

    for index, key in enumerate(problem_keys, 1):
        try:
            product = service.generate(
                key,
                persist=True,
            )

            results.append(
                {
                    "problem_key": key,
                    "product_id": product.get("id"),
                    "probability": product.get("probability"),
                    "confidence": product.get("confidence"),
                    "trend": product.get("trend"),
                }
            )

            probability = product.get("probability")
            confidence = product.get("confidence")
            confidence_status = product.get(
                "confidence_status"
            )

            probability_text = (
                f"{float(probability):.4f}"
                if probability is not None
                else "N/A"
            )

            confidence_text = (
                f"{float(confidence):.2f}"
                if confidence is not None
                else (
                    confidence_status
                    or "INSUFFICIENT_EVIDENCE"
                )
            )

            print(
                f"[{index}/{len(problem_keys)}] ✅ {key} | "
                f"p={probability_text} "
                f"confidence={confidence_text}"
            )

        except Exception as exc:
            errors.append(
                {
                    "problem_key": key,
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )

            print(
                f"[{index}/{len(problem_keys)}] ❌ {key} | "
                f"{type(exc).__name__}: {exc}"
            )

    summary = {
        "requested_problem_keys": (
            args.problem_keys or []
        ),
        "incremental_mode": bool(args.problem_keys),
        "warning_problems_processed": len(problem_keys),
        "products_generated": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }

    print("\n" + "=" * 80)
    print("SEWS STRATEGIC INTELLIGENCE PRODUCT SUMMARY")
    print("=" * 80)
    pprint(summary)


if __name__ == "__main__":
    main()
