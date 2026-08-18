from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from supabase import Client, create_client


class ConflictRepositoryError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ConflictRepositoryError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) are required."
        )
    return create_client(url, key)


class ConflictIntelligenceRepository:
    TABLES = {
        "countries": "conflict_countries",
        "dyads": "conflict_border_dyads",
        "territories": "conflict_territories",
        "frozen_conflicts": "conflict_frozen_conflicts",
        "actors": "conflict_armed_actors",
        "episodes": "conflict_episodes",
        "disputes": "conflict_disputes",
        "non_state_organizations": "conflict_non_state_organizations",
        "governing_authorities": "conflict_governing_authorities",
        "country_aliases": "conflict_country_aliases",
        "observations": "conflict_observations",
        "current_states": "conflict_current_state",
        "state_history": "conflict_state_history",
        "state_timeline": "conflict_state_timeline",
        "state_transitions": "conflict_state_transitions",
        "propagation_edges": "conflict_propagation_edges",
        "ripple_runs": "conflict_ripple_runs",
        "historical_episodes": "conflict_historical_episodes",
        "snapshots": "conflict_snapshots",
    }

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    def list_records(
        self,
        entity: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        table = self.TABLES.get(entity)
        if table is None:
            raise ConflictRepositoryError(f"Unsupported entity: {entity}")

        query = self.client.table(table).select("*", count="exact")
        for key, value in (filters or {}).items():
            if value is not None:
                query = query.eq(key, value)

        response = query.range(offset, offset + limit - 1).execute()
        return response.data or [], int(response.count or 0)

    def get_record(self, entity: str, key: str, value: str) -> dict[str, Any] | None:
        table = self.TABLES.get(entity)
        if table is None:
            raise ConflictRepositoryError(f"Unsupported entity: {entity}")
        response = self.client.table(table).select("*").eq(key, value).limit(1).execute()
        return response.data[0] if response.data else None

    def count(self, entity: str, filters: dict[str, Any] | None = None) -> int:
        table = self.TABLES.get(entity)
        if table is None:
            raise ConflictRepositoryError(f"Unsupported entity: {entity}")
        query = self.client.table(table).select("id", count="exact", head=True)
        for key, value in (filters or {}).items():
            if value is not None:
                query = query.eq(key, value)
        response = query.execute()
        return int(response.count or 0)
