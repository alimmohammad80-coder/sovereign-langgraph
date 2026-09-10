from __future__ import annotations

import argparse
import asyncio
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_portfolio_refresh_service import SEWSPortfolioRefreshService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the production SEWS portfolio refresh. Legacy checkpoint flags are "
            "accepted for Render command compatibility but no local checkpoint is used."
        )
    )
    parser.add_argument("--mode", choices=("once", "forever"), default="once")
    parser.add_argument("--interval-minutes", type=int, default=60)
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["GOOGLE_NEWS_RSS", "GDELT"],
        help="Legacy compatibility option. Production refresh uses its query-safe source registry.",
    )
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--limit-per-query", type=int, default=3)
    parser.add_argument("--reset-collection-checkpoint", action="store_true")
    parser.add_argument("--reset-incremental-checkpoint", action="store_true")
    parser.add_argument("--clear-stale-lock", action="store_true")
    return parser.parse_args()


async def run_once(args: argparse.Namespace) -> dict:
    db = get_sews_supabase_client()
    return await SEWSPortfolioRefreshService(db).refresh(
        concurrency=max(1, min(args.batch_size, 4)),
        limit_per_query=max(1, min(args.limit_per_query, 20)),
    )


async def main() -> None:
    args = parse_args()

    if (
        args.reset_collection_checkpoint
        or args.reset_incremental_checkpoint
        or args.clear_stale_lock
    ):
        print(
            "ℹ️ Legacy checkpoint/lock flags were supplied but are no longer needed; "
            "the production workflow uses persisted database evidence instead of .sews state files."
        )

    if args.mode == "forever":
        while True:
            result = await run_once(args)
            print("\n" + "=" * 80)
            print("SEWS PRODUCTION PORTFOLIO REFRESH SUMMARY")
            print("=" * 80)
            pprint(result)
            await asyncio.sleep(max(1, args.interval_minutes) * 60)

    result = await run_once(args)
    print("\n" + "=" * 80)
    print("SEWS PRODUCTION PORTFOLIO REFRESH SUMMARY")
    print("=" * 80)
    pprint(result)


if __name__ == "__main__":
    asyncio.run(main())
