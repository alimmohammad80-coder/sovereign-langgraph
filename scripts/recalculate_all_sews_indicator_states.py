from __future__ import annotations

from collections import Counter, defaultdict
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_evidence import IndicatorStateRecalculateRequest
from app.services.sews_indicator_state_service import (
    SEWSIndicatorStateService,
)


def fetch_all(db, table: str, columns: str, page_size: int = 1000):
    rows = []
    start = 0

    while True:
        batch = (
            db.table(table)
            .select(columns)
            .range(start, start + page_size - 1)
            .execute()
            .data
            or []
        )

        rows.extend(batch)

        if len(batch) < page_size:
            break

        start += page_size

    return rows


def main() -> None:
    db = get_sews_supabase_client()
    service = SEWSIndicatorStateService(db)

    nodes = fetch_all(
        db,
        "sews_causal_nodes",
        "id,problem_key",
    )

    node_problem = {
        str(row["id"]): row["problem_key"]
        for row in nodes
        if row.get("id") and row.get("problem_key")
    }

    links = fetch_all(
        db,
        "sews_causal_node_indicator_links",
        "node_id,indicator_key,active",
    )

    contexts = sorted({
        (
            node_problem.get(str(link["node_id"])),
            link["indicator_key"],
        )
        for link in links
        if (
            link.get("active", True)
            and link.get("indicator_key")
            and node_problem.get(str(link["node_id"]))
        )
    })

    status_counts = Counter()
    coverage = defaultdict(
        lambda: {
            "processed": 0,
            "active": 0,
            "degraded": 0,
            "stale": 0,
            "insufficient": 0,
            "failed": 0,
        }
    )

    errors = []

    for index, (problem_key, indicator_key) in enumerate(
        contexts,
        start=1,
    ):
        try:
            state = service.recalculate(
                IndicatorStateRecalculateRequest(
                    indicator_key=indicator_key,
                    warning_problem_key=problem_key,
                    lookback_days=30,
                    stale_after_hours=72,
                    minimum_evidence=2,
                )
            )

            status = str(
                getattr(state.status, "value", state.status)
            ).upper()

            status_counts[status] += 1
            coverage[problem_key]["processed"] += 1

            if status == "ACTIVE":
                coverage[problem_key]["active"] += 1
            elif status == "DEGRADED":
                coverage[problem_key]["degraded"] += 1
            elif status == "STALE":
                coverage[problem_key]["stale"] += 1
            else:
                coverage[problem_key]["insufficient"] += 1

            print(
                f"[{index}/{len(contexts)}] "
                f"{problem_key} | {indicator_key} | {status}"
            )

        except Exception as exc:
            coverage[problem_key]["processed"] += 1
            coverage[problem_key]["failed"] += 1
            errors.append({
                "problem_key": problem_key,
                "indicator_key": indicator_key,
                "error": f"{type(exc).__name__}: {exc}",
            })

            print(
                f"[{index}/{len(contexts)}] "
                f"❌ {problem_key} | {indicator_key} | "
                f"{type(exc).__name__}: {exc}"
            )

    summary = {
        "indicator_contexts_processed": len(contexts),
        "successful": len(contexts) - len(errors),
        "failed": len(errors),
        "status_counts": dict(status_counts),
        "coverage_by_problem": dict(sorted(coverage.items())),
        "errors": errors[:50],
    }

    print("\n" + "=" * 80)
    print("GLOBAL SEWS INDICATOR-STATE RECALCULATION SUMMARY")
    print("=" * 80)
    pprint(summary)


if __name__ == "__main__":
    main()
