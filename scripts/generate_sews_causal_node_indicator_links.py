from __future__ import annotations

from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_causal_node_indicator_link_generator import (
    SEWSCausalNodeIndicatorLinkGenerator,
)


def main() -> None:
    db = get_sews_supabase_client()
    pprint(SEWSCausalNodeIndicatorLinkGenerator(db).generate_all())


if __name__ == "__main__":
    main()
