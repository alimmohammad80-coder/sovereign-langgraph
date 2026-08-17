from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone


def run_step(name: str, command: list[str]) -> None:
    print("\n" + "=" * 100)
    print(name)
    print("=" * 100)
    print("COMMAND:", " ".join(command))
    print("STARTED:", datetime.now(timezone.utc).isoformat())

    result = subprocess.run(
        command,
        check=False,
    )

    if result.returncode != 0:
        raise SystemExit(
            f"{name} failed with return code "
            f"{result.returncode}"
        )

    print(
        "FINISHED:",
        datetime.now(timezone.utc).isoformat(),
    )


def main() -> None:
    python = sys.executable

    print("=" * 100)
    print("SEWS DAILY INTELLIGENCE REFRESH")
    print("=" * 100)
    print(
        "Started:",
        datetime.now(timezone.utc).isoformat(),
    )

    # 1. Refresh every indicator state from current evidence.
    run_step(
        "STEP 1 — RECALCULATE INDICATOR STATES",
        [
            python,
            "scripts/recalculate_all_sews_indicator_states.py",
        ],
    )

    # 2. Reassess the complete warning portfolio.
    #
    # This performs the deterministic assessment and AI strategic
    # review pipeline using the newly refreshed indicator states.
    run_step(
        "STEP 2 — RUN ALL WARNING SUPERVISORS",
        [
            python,
            "scripts/run_all_sews_warning_supervisors.py",
        ],
    )

    # 3. Publish a current intelligence product for the complete
    # portfolio. Daily products are intentionally refreshed even
    # where the warning judgment remains unchanged.
    run_step(
        "STEP 3 — GENERATE INTELLIGENCE PRODUCTS",
        [
            python,
            "scripts/generate_all_sews_intelligence_products.py",
        ],
    )

    print("\n" + "=" * 100)
    print("SEWS DAILY INTELLIGENCE REFRESH COMPLETE")
    print("=" * 100)
    print(
        "Finished:",
        datetime.now(timezone.utc).isoformat(),
    )


if __name__ == "__main__":
    main()
