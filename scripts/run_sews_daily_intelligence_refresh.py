from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_environment() -> dict[str, str]:
    env = os.environ.copy()
    env_path = Path(".env")

    if env_path.exists():
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key:
                env[key] = value

    return env


def run_step(
    name: str,
    command: list[str],
    env: dict[str, str],
) -> None:
    print("\n" + "=" * 100)
    print(name)
    print("=" * 100)
    print("COMMAND:", " ".join(command))
    print("STARTED:", datetime.now(timezone.utc).isoformat())

    result = subprocess.run(
        command,
        check=False,
        env=env,
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
    env = load_environment()

    required = (
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
    )

    missing = [
        key
        for key in required
        if not env.get(key)
    ]

    if missing:
        raise SystemExit(
            "Missing required environment variables: "
            + ", ".join(missing)
        )

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
        env,
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
        env,
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
        env,
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
