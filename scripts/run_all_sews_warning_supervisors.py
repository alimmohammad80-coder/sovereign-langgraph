from __future__ import annotations

import asyncio
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_operations import WarningSupervisorRunRequest
from app.services.sews_warning_supervisor import SEWSWarningSupervisor


async def main() -> None:
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

    supervisor = SEWSWarningSupervisor(db)

    results = []
    errors = []

    completed = {"WP-AFG-CROSS-BORDER-MILITANCY"}

    remaining = [
        row
        for row in problems
        if row["problem_key"] not in completed
    ]

    for index, row in enumerate(remaining, 1):
        problem_key = row["problem_key"]

        try:
            result = await supervisor.run(
                WarningSupervisorRunRequest(
                    problem_key=problem_key,
                    dry_run=False,
                    limit_per_query=5,
                )
            )

            item = result.model_dump(mode="json")
            results.append(item)

            print(
                f"[{index}/{len(problems)}] ✅ {problem_key} | "
                f"status={item.get('status')} "
                f"received={item.get('records_received')} "
                f"persisted={item.get('records_persisted')} "
                f"matched={item.get('indicators_matched')} "
                f"observations={item.get('observations_created')} "
                f"states={item.get('states_recalculated')}"
            )

            if item.get("errors"):
                print("   Errors:", item["errors"])

        except Exception as exc:
            error = {
                "problem_key": problem_key,
                "error": f"{type(exc).__name__}: {exc}",
            }
            errors.append(error)

            print(
                f"[{index}/{len(problems)}] ❌ {problem_key} | "
                f"{error['error']}"
            )

    summary = {
        "warning_problems_processed": len(problems),
        "successful_runs": len(results),
        "failed_runs": len(errors),
        "records_received": sum(
            int(item.get("records_received") or 0)
            for item in results
        ),
        "records_persisted": sum(
            int(item.get("records_persisted") or 0)
            for item in results
        ),
        "indicators_matched": sum(
            int(item.get("indicators_matched") or 0)
            for item in results
        ),
        "observations_created": sum(
            int(item.get("observations_created") or 0)
            for item in results
        ),
        "states_recalculated": sum(
            int(item.get("states_recalculated") or 0)
            for item in results
        ),
        "errors": errors,
    }

    print("\n" + "=" * 80)
    print("GLOBAL SEWS WARNING-SUPERVISOR SUMMARY")
    print("=" * 80)
    pprint(summary)


if __name__ == "__main__":
    asyncio.run(main())
