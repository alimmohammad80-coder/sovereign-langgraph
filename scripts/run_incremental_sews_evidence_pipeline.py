from __future__ import annotations

import argparse
from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_incremental_evidence_pipeline import (
    IncrementalPipelineConfig,
    SEWSIncrementalEvidencePipeline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process only newly collected SEWS evidence."
    )
    parser.add_argument(
        "--checkpoint",
        default=".sews/incremental_evidence_checkpoint.json",
    )
    parser.add_argument("--reset-checkpoint", action="store_true")
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument("--stale-after-hours", type=int, default=72)
    parser.add_argument("--minimum-evidence", type=int, default=2)
    parser.add_argument(
        "--no-persist-causal",
        action="store_true",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = get_sews_supabase_client()

    result = SEWSIncrementalEvidencePipeline(db).run(
        IncrementalPipelineConfig(
            checkpoint_path=args.checkpoint,
            lookback_days=max(1, args.lookback_days),
            stale_after_hours=max(1, args.stale_after_hours),
            minimum_evidence=max(1, args.minimum_evidence),
            persist_causal_assessments=not args.no_persist_causal,
            reset_checkpoint=args.reset_checkpoint,
        )
    )

    print("\n" + "=" * 80)
    print("SEWS INCREMENTAL EVIDENCE PIPELINE SUMMARY")
    print("=" * 80)
    pprint(result)


if __name__ == "__main__":
    main()
