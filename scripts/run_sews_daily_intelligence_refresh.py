from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_portfolio_refresh_service import SEWSPortfolioRefreshService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the production SEWS daily portfolio refresh: collect evidence once, "
            "create canonical evidence/observations, recalculate states, reassess, "
            "and publish evidence-grounded OA/2.0 products."
        )
    )
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--limit-per-query", type=int, default=5)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    db = get_sews_supabase_client()

    print("=" * 100)
    print("SEWS DAILY PRODUCTION REFRESH — OA/2.0")
    print("=" * 100)
    print("Started:", datetime.now(timezone.utc).isoformat())

    result = await SEWSPortfolioRefreshService(db).refresh(
        concurrency=max(1, min(args.concurrency, 4)),
        limit_per_query=max(1, min(args.limit_per_query, 20)),
    )

    print("\n" + "=" * 100)
    print("SEWS DAILY PRODUCTION REFRESH SUMMARY")
    print("=" * 100)
    pprint(result)
    print("Finished:", datetime.now(timezone.utc).isoformat())

    if result.get("status") not in {"success", "partial"}:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
