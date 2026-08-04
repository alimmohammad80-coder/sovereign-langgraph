from __future__ import annotations

import argparse
import asyncio
from pprint import pprint

from app.routes.sews_evidence import (
    get_sews_supabase_client,
)
from app.services.sews_scheduled_intelligence_workflow import (
    ScheduledWorkflowConfig,
    SEWSScheduledIntelligenceWorkflow,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the checkpointed SEWS collection and "
            "incremental-processing workflow."
        )
    )

    parser.add_argument(
        "--mode",
        choices=("once", "forever"),
        default="once",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=60,
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["GOOGLE_NEWS_RSS", "GDELT"],
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
    )
    parser.add_argument(
        "--limit-per-query",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--reset-collection-checkpoint",
        action="store_true",
    )
    parser.add_argument(
        "--reset-incremental-checkpoint",
        action="store_true",
    )
    parser.add_argument(
        "--clear-stale-lock",
        action="store_true",
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    db = get_sews_supabase_client()

    config = ScheduledWorkflowConfig(
        source_keys=tuple(args.sources),
        limit_per_query=max(
            1,
            args.limit_per_query,
        ),
        problem_batch_size=max(
            1,
            args.batch_size,
        ),
        interval_minutes=max(
            1,
            args.interval_minutes,
        ),
    )

    workflow = SEWSScheduledIntelligenceWorkflow(db)

    if args.clear_stale_lock:
        workflow.clear_stale_lock(config)
        print("✅ Stale workflow lock cleared.")

    if args.mode == "forever":
        await workflow.run_forever(config)
        return

    result = await workflow.run_once(
        config,
        reset_collection_checkpoint=(
            args.reset_collection_checkpoint
        ),
        reset_incremental_checkpoint=(
            args.reset_incremental_checkpoint
        ),
    )

    print("\n" + "=" * 80)
    print("SEWS SCHEDULED WORKFLOW SUMMARY")
    print("=" * 80)
    pprint(result)


if __name__ == "__main__":
    asyncio.run(main())
