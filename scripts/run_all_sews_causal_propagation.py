from __future__ import annotations

from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_causal_propagation_runner import (
    SEWSCausalPropagationRunner,
)


def main() -> None:
    db = get_sews_supabase_client()

    result = SEWSCausalPropagationRunner(
        db
    ).run_all(
        persist=True,
    )

    print("\n" + "=" * 80)
    print("GLOBAL SEWS CAUSAL PROPAGATION SUMMARY")
    print("=" * 80)
    pprint(result)


if __name__ == "__main__":
    main()
