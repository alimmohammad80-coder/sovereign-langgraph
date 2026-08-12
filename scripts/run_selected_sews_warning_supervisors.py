from __future__ import annotations

import argparse
import asyncio
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_operations import WarningSupervisorRunRequest
from app.services.sews_warning_supervisor import SEWSWarningSupervisor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run SEWS warning supervisors only for explicitly "
            "selected warning problems."
        )
    )

    parser.add_argument(
        "--problem-keys",
        nargs="+",
        required=True,
    )

    parser.add_argument(
        "--limit-per-query",
        type=int,
        default=3,
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    problem_keys = list(
        dict.fromkeys(
            str(key).strip()
            for key in args.problem_keys
            if str(key).strip()
        )
    )

    db = get_sews_supabase_client()
    supervisor = SEWSWarningSupervisor(db)

    results = []
    failures = []
    material_changed_problem_keys = []

    for index, problem_key in enumerate(problem_keys, 1):
        try:
            result = await supervisor.run(
                WarningSupervisorRunRequest(
                    problem_key=problem_key,
                    dry_run=False,
                    limit_per_query=max(
                        1,
                        args.limit_per_query,
                    ),
                )
            )

            item = result.model_dump(mode="json")
            results.append(item)

            if item.get("material_change"):
                material_changed_problem_keys.append(
                    problem_key
                )

            print(
                f"[{index}/{len(problem_keys)}] "
                f"{problem_key} | "
                f"status={item.get('status')} "
                f"received={item.get('records_received')} "
                f"persisted={item.get('records_persisted')} "
                f"matched={item.get('indicators_matched')} "
                f"observations={item.get('observations_created')} "
                f"states={item.get('states_recalculated')} "
                f"material_change={item.get('material_change')}"
            )

            if item.get("errors"):
                print(
                    "   Non-blocking errors:",
                    item["errors"],
                )

        except Exception as exc:
            failure = {
                "problem_key": problem_key,
                "error": (
                    f"{type(exc).__name__}: {exc}"
                ),
            }

            failures.append(failure)

            print(
                f"[{index}/{len(problem_keys)}] "
                f"FAILED {problem_key}: "
                f"{failure['error']}"
            )

    summary = {
        "warning_problems_requested": len(
            problem_keys
        ),
        "warning_problems_processed": len(
            results
        ),
        "failed_runs": len(failures),
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
        "material_changed_problem_keys": sorted(
            set(material_changed_problem_keys)
        ),
        "material_changed_count": len(
            set(material_changed_problem_keys)
        ),
        "errors": failures,
    }

    print()
    print("=" * 80)
    print("SELECTIVE SEWS WARNING SUPERVISOR SUMMARY")
    print("=" * 80)
    pprint(summary)


if __name__ == "__main__":
    asyncio.run(main())
