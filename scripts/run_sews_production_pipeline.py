from __future__ import annotations

import argparse
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_pipeline_orchestrator import SEWSPipelineOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the unified auditable SEWS production pipeline."
    )
    parser.add_argument("--mode", choices=("once", "forever"), default="once")
    parser.add_argument("--interval-minutes", type=int, default=60)
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["GOOGLE_NEWS_RSS", "GDELT"],
    )
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--limit-per-query", type=int, default=3)
    parser.add_argument(
        "--no-reset-collection-checkpoint",
        action="store_true",
    )
    parser.add_argument(
        "--skip-products",
        action="store_true",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = get_sews_supabase_client()
    orchestrator = SEWSPipelineOrchestrator(db)

    kwargs = {
        "source_keys": args.sources,
        "batch_size": args.batch_size,
        "limit_per_query": args.limit_per_query,
        "reset_collection_checkpoint": (
            not args.no_reset_collection_checkpoint
        ),
        "generate_products": not args.skip_products,
    }

    if args.mode == "forever":
        orchestrator.run_forever(
            interval_minutes=args.interval_minutes,
            **kwargs,
        )
        return

    pprint(orchestrator.run_once(**kwargs))


if __name__ == "__main__":
    main()
