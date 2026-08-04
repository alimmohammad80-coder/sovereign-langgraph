from __future__ import annotations

import argparse
import asyncio
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_global_intelligence_collector import (
    DEFAULT_SOURCE_KEYS,
    GlobalCollectionConfig,
    SEWSGlobalIntelligenceCollector,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run resumable global SEWS intelligence collection."
    )
    parser.add_argument("--limit-per-query", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--sources", nargs="+", default=list(DEFAULT_SOURCE_KEYS))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--reset-checkpoint", action="store_true")
    parser.add_argument(
        "--checkpoint",
        default=".sews/global_collection_checkpoint.json",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    db = get_sews_supabase_client()
    result = await SEWSGlobalIntelligenceCollector(db).collect_all(
        GlobalCollectionConfig(
            source_keys=tuple(args.sources),
            limit_per_query=max(1, args.limit_per_query),
            problem_batch_size=max(1, args.batch_size),
            persist=not args.dry_run,
            dry_run=args.dry_run,
            checkpoint_path=args.checkpoint,
        ),
        resume=not args.no_resume,
        reset_checkpoint=args.reset_checkpoint,
    )
    print("\n" + "=" * 80)
    print("GLOBAL SEWS INTELLIGENCE COLLECTION SUMMARY")
    print("=" * 80)
    pprint(result)


if __name__ == "__main__":
    asyncio.run(main())
