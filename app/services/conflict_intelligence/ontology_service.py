from __future__ import annotations

from typing import Any

from app.repositories.conflict_intelligence_repository import ConflictIntelligenceRepository


class OntologyService:
    def __init__(self, repository: ConflictIntelligenceRepository | None = None) -> None:
        self.repository = repository or ConflictIntelligenceRepository()

    def list_entity(
        self,
        entity: str,
        *,
        filters: dict[str, Any],
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        rows, count = self.repository.list_records(
            entity,
            filters=filters,
            limit=limit,
            offset=offset,
        )
        return {
            "items": rows,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": count,
            },
        }

    def summary(self) -> dict[str, Any]:
        entity_counts = {
            "countries": self.repository.count("countries"),
            "border_dyads": self.repository.count("dyads"),
            "territories": self.repository.count("territories"),
            "frozen_conflicts": self.repository.count("frozen_conflicts"),
            "armed_actors": self.repository.count("actors"),
            "conflict_episodes": self.repository.count("episodes"),
            "disputes": self.repository.count("disputes"),
            "non_state_organizations": self.repository.count("non_state_organizations"),
            "governing_authorities": self.repository.count("governing_authorities"),
            "historical_episodes": self.repository.count("historical_episodes"),
        }

        validated = (
            self.repository.count("countries", {"review_status": "validated"})
            + self.repository.count("dyads", {"review_status": "validated"})
            + self.repository.count("territories", {"review_status": "validated"})
            + self.repository.count("frozen_conflicts", {"review_status": "validated"})
            + self.repository.count("actors", {"review_status": "validated"})
            + self.repository.count("episodes", {"review_status": "validated"})
            + self.repository.count("disputes", {"review_status": "validated"})
            + self.repository.count("non_state_organizations", {"review_status": "validated"})
            + self.repository.count("governing_authorities", {"review_status": "validated"})
            + self.repository.count("historical_episodes", {"review_status": "validated"})
        )
        provisional = (
            self.repository.count("countries", {"review_status": "provisional"})
            + self.repository.count("dyads", {"review_status": "provisional"})
            + self.repository.count("territories", {"review_status": "provisional"})
            + self.repository.count("frozen_conflicts", {"review_status": "provisional"})
            + self.repository.count("actors", {"review_status": "provisional"})
            + self.repository.count("episodes", {"review_status": "provisional"})
            + self.repository.count("disputes", {"review_status": "provisional"})
            + self.repository.count("non_state_organizations", {"review_status": "provisional"})
            + self.repository.count("governing_authorities", {"review_status": "provisional"})
            + self.repository.count("historical_episodes", {"review_status": "provisional"})
        )

        return {
            "ontology_version": "conflict-intelligence-ontology-v1",
            **entity_counts,
            "validated_records": validated,
            "provisional_records": provisional,
            "last_snapshot_id": None,
            "last_updated": None,
        }
