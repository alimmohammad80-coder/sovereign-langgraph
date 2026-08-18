from __future__ import annotations

import hashlib
from collections import Counter
from datetime import date
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


GRAPH_VERSION = "conflict-propagation-graph-v1"


CHANNEL_BY_RELATIONSHIP = {
    "shares_border": "security_spillover",
    "has_dyad": "security_spillover",
    "dyad_member": "security_spillover",

    "party_to_dispute": "security_spillover",
    "dispute_has_party": "security_spillover",

    "dispute_to_frozen_conflict": "security_spillover",
    "frozen_conflict_to_dispute": "security_spillover",

    "dispute_over_territory": "security_spillover",
    "territory_subject_of_dispute": "security_spillover",

    "episode_has_participant": "security_spillover",
    "participant_in_episode": "security_spillover",

    "episode_involves_territory": "security_spillover",
    "territory_in_episode": "security_spillover",
}


WEIGHTS = {
    "shares_border": 0.55,

    "has_dyad": 0.85,
    "dyad_member": 0.85,

    "party_to_dispute": 0.80,
    "dispute_has_party": 0.80,

    "dispute_to_frozen_conflict": 0.90,
    "frozen_conflict_to_dispute": 0.90,

    "dispute_over_territory": 0.85,
    "territory_subject_of_dispute": 0.85,

    "episode_has_participant": 0.90,
    "participant_in_episode": 0.90,

    "episode_involves_territory": 0.80,
    "territory_in_episode": 0.80,
}


CONFIDENCE = {
    "shares_border": 95,
    "has_dyad": 100,
    "dyad_member": 100,

    "party_to_dispute": 95,
    "dispute_has_party": 95,

    "dispute_to_frozen_conflict": 100,
    "frozen_conflict_to_dispute": 100,

    "dispute_over_territory": 95,
    "territory_subject_of_dispute": 95,

    "episode_has_participant": 95,
    "participant_in_episode": 95,

    "episode_involves_territory": 90,
    "territory_in_episode": 90,
}


class PropagationGraphBuilder:

    def __init__(self) -> None:
        self.db = get_supabase_client()

        self.edges: dict[
            str,
            dict[str, Any],
        ] = {}

    @staticmethod
    def _normalize_node(
        value: Any,
    ) -> str | None:

        if value is None:
            return None

        value = str(
            value
        ).strip()

        if not value:
            return None

        return value

    @staticmethod
    def _edge_key(
        source_node: str,
        relationship: str,
        target_node: str,
    ) -> str:

        raw = (
            f"{source_node}|"
            f"{relationship}|"
            f"{target_node}"
        )

        digest = hashlib.sha256(
            raw.encode()
        ).hexdigest()[:24].upper()

        return f"PEDGE-{digest}"

    def _add_edge(
        self,
        *,
        source_node: Any,
        source_type: str,
        target_node: Any,
        target_type: str,
        relationship: str,
        source: str,
        source_version: str | None = None,
        transmission_weight: float | None = None,
        damping_factor: float = 1.0,
        confidence: float | None = None,
    ) -> None:

        source_node = (
            self._normalize_node(
                source_node
            )
        )

        target_node = (
            self._normalize_node(
                target_node
            )
        )

        if (
            source_node is None
            or target_node is None
            or source_node == target_node
        ):
            return

        edge_key = self._edge_key(
            source_node,
            relationship,
            target_node,
        )

        weight = (
            transmission_weight
            if transmission_weight
            is not None
            else WEIGHTS.get(
                relationship,
                0.50,
            )
        )

        edge_confidence = (
            confidence
            if confidence is not None
            else CONFIDENCE.get(
                relationship,
                75,
            )
        )

        self.edges[
            edge_key
        ] = {
            "edge_key":
                edge_key,

            "source_node":
                source_node,

            "source_type":
                source_type,

            "target_node":
                target_node,

            "target_type":
                target_type,

            "relationship":
                relationship,

            "channel":
                CHANNEL_BY_RELATIONSHIP.get(
                    relationship,
                    "security_spillover",
                ),

            "transmission_weight":
                round(
                    float(weight),
                    6,
                ),

            "damping_factor":
                round(
                    float(
                        damping_factor
                    ),
                    6,
                ),

            "confidence":
                round(
                    float(
                        edge_confidence
                    ),
                    1,
                ),

            "method":
                "ontology-derived",

            "source":
                source,

            "source_version":
                source_version,

            "active":
                True,

            "review_status":
                "validated",

            "last_reviewed":
                date.today().isoformat(),
        }

    def _build_border_dyads(
        self,
    ) -> None:

        rows = (
            self.db.table(
                "conflict_border_dyads"
            )
            .select(
                "dyad_id,"
                "country_a_iso3,"
                "country_b_iso3,"
                "source,"
                "source_version"
            )
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        for row in rows:

            a = row.get(
                "country_a_iso3"
            )

            b = row.get(
                "country_b_iso3"
            )

            dyad = row.get(
                "dyad_id"
            )

            source = (
                row.get(
                    "source"
                )
                or "conflict_border_dyads"
            )

            version = row.get(
                "source_version"
            )

            # Direct state-to-state spillover.
            self._add_edge(
                source_node=a,
                source_type="country",
                target_node=b,
                target_type="country",
                relationship="shares_border",
                source=source,
                source_version=version,
            )

            self._add_edge(
                source_node=b,
                source_type="country",
                target_node=a,
                target_type="country",
                relationship="shares_border",
                source=source,
                source_version=version,
            )

            # Country ↔ dyad ontology.
            for country in [
                a,
                b,
            ]:

                self._add_edge(
                    source_node=country,
                    source_type="country",
                    target_node=dyad,
                    target_type="dyad",
                    relationship="has_dyad",
                    source=source,
                    source_version=version,
                )

                self._add_edge(
                    source_node=dyad,
                    source_type="dyad",
                    target_node=country,
                    target_type="country",
                    relationship="dyad_member",
                    source=source,
                    source_version=version,
                )

    def _build_disputes(
        self,
    ) -> None:

        rows = (
            self.db.table(
                "conflict_disputes"
            )
            .select(
                "dispute_id,"
                "claimant_iso3,"
                "primary_dyad_id,"
                "territory_id,"
                "source,"
                "source_version"
            )
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        for row in rows:

            dispute_id = row.get(
                "dispute_id"
            )

            source = (
                row.get(
                    "source"
                )
                or "conflict_disputes"
            )

            version = row.get(
                "source_version"
            )

            for country in (
                row.get(
                    "claimant_iso3"
                )
                or []
            ):

                self._add_edge(
                    source_node=country,
                    source_type="country",
                    target_node=dispute_id,
                    target_type="dispute",
                    relationship="party_to_dispute",
                    source=source,
                    source_version=version,
                )

                self._add_edge(
                    source_node=dispute_id,
                    source_type="dispute",
                    target_node=country,
                    target_type="country",
                    relationship="dispute_has_party",
                    source=source,
                    source_version=version,
                )

            territory = row.get(
                "territory_id"
            )

            if territory:

                self._add_edge(
                    source_node=dispute_id,
                    source_type="dispute",
                    target_node=territory,
                    target_type="territory",
                    relationship="dispute_over_territory",
                    source=source,
                    source_version=version,
                )

                self._add_edge(
                    source_node=territory,
                    source_type="territory",
                    target_node=dispute_id,
                    target_type="dispute",
                    relationship="territory_subject_of_dispute",
                    source=source,
                    source_version=version,
                )

            dyad = row.get(
                "primary_dyad_id"
            )

            if dyad:

                self._add_edge(
                    source_node=dyad,
                    source_type="dyad",
                    target_node=dispute_id,
                    target_type="dispute",
                    relationship="party_to_dispute",
                    source=source,
                    source_version=version,
                    transmission_weight=0.90,
                    confidence=100,
                )

    def _build_frozen_conflicts(
        self,
    ) -> None:

        rows = (
            self.db.table(
                "conflict_frozen_conflicts"
            )
            .select(
                "fc_id,"
                "dispute_id,"
                "territory_id,"
                "primary_dyad_id,"
                "source,"
                "source_version"
            )
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        for row in rows:

            fc_id = row.get(
                "fc_id"
            )

            dispute_id = row.get(
                "dispute_id"
            )

            source = (
                row.get(
                    "source"
                )
                or "conflict_frozen_conflicts"
            )

            version = row.get(
                "source_version"
            )

            if dispute_id:

                self._add_edge(
                    source_node=dispute_id,
                    source_type="dispute",
                    target_node=fc_id,
                    target_type="frozen_conflict",
                    relationship="dispute_to_frozen_conflict",
                    source=source,
                    source_version=version,
                )

                self._add_edge(
                    source_node=fc_id,
                    source_type="frozen_conflict",
                    target_node=dispute_id,
                    target_type="dispute",
                    relationship="frozen_conflict_to_dispute",
                    source=source,
                    source_version=version,
                )

            territory = row.get(
                "territory_id"
            )

            if territory:

                self._add_edge(
                    source_node=fc_id,
                    source_type="frozen_conflict",
                    target_node=territory,
                    target_type="territory",
                    relationship="dispute_over_territory",
                    source=source,
                    source_version=version,
                )

            dyad = row.get(
                "primary_dyad_id"
            )

            if dyad:

                self._add_edge(
                    source_node=dyad,
                    source_type="dyad",
                    target_node=fc_id,
                    target_type="frozen_conflict",
                    relationship="dispute_to_frozen_conflict",
                    source=source,
                    source_version=version,
                    transmission_weight=0.95,
                    confidence=100,
                )

    def _territory_lookup(
        self,
    ) -> dict[str, str]:

        rows = (
            self.db.table(
                "conflict_territories"
            )
            .select(
                "territory_id,"
                "name,"
                "geometry_ref"
            )
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        lookup = {}

        for row in rows:

            territory_id = row.get(
                "territory_id"
            )

            if not territory_id:
                continue

            values = [
                territory_id,
                row.get("name"),
                row.get("geometry_ref"),
            ]

            for value in values:

                if not value:
                    continue

                normalized = (
                    str(value)
                    .strip()
                    .lower()
                )

                lookup[
                    normalized
                ] = territory_id

                # Helpful aliases from compound names.
                if "/" in normalized:
                    for part in normalized.split("/"):
                        part = part.strip()

                        if part:
                            lookup[
                                part
                            ] = territory_id

        # Explicit ontology aliases where the historical
        # dataset uses abbreviated territorial labels.
        lookup[
            "kashmir"
        ] = "TERRITORY-KASHMIR"

        return lookup

    def _build_episodes(
        self,
    ) -> None:

        territory_lookup = (
            self._territory_lookup()
        )

        rows = (
            self.db.table(
                "conflict_canonical_episodes"
            )
            .select(
                "id,"
                "conflict_id,"
                "state_participants,"
                "territories"
            )
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        for row in rows:

            episode_node = (
                f"EPISODE-{row['conflict_id']}"
            )

            for country in (
                row.get(
                    "state_participants"
                )
                or []
            ):

                self._add_edge(
                    source_node=episode_node,
                    source_type="conflict_episode",
                    target_node=country,
                    target_type="country",
                    relationship="episode_has_participant",
                    source="UCDP/PRIO canonical episode",
                    source_version="26.1",
                )

                self._add_edge(
                    source_node=country,
                    source_type="country",
                    target_node=episode_node,
                    target_type="conflict_episode",
                    relationship="participant_in_episode",
                    source="UCDP/PRIO canonical episode",
                    source_version="26.1",
                )

            territories = row.get(
                "territories"
            )

            if isinstance(
                territories,
                str,
            ):
                territories = [
                    territories
                ]

            for territory in (
                territories
                or []
            ):

                raw_territory = str(
                    territory
                ).strip()

                canonical_territory = (
                    territory_lookup.get(
                        raw_territory.lower()
                    )
                    or raw_territory
                )

                self._add_edge(
                    source_node=episode_node,
                    source_type="conflict_episode",
                    target_node=canonical_territory,
                    target_type="territory",
                    relationship="episode_involves_territory",
                    source="UCDP/PRIO canonical episode",
                    source_version="26.1",
                )

                self._add_edge(
                    source_node=canonical_territory,
                    source_type="territory",
                    target_node=episode_node,
                    target_type="conflict_episode",
                    relationship="territory_in_episode",
                    source="UCDP/PRIO canonical episode",
                    source_version="26.1",
                )

    def build(
        self,
    ) -> dict[str, Any]:

        self.edges = {}

        self._build_border_dyads()
        self._build_disputes()
        self._build_frozen_conflicts()
        self._build_episodes()

        records = list(
            self.edges.values()
        )

        relationship_counts = Counter(
            row[
                "relationship"
            ]
            for row in records
        )

        channel_counts = Counter(
            row[
                "channel"
            ]
            for row in records
        )

        node_types = Counter()

        nodes = set()

        for row in records:

            nodes.add(
                (
                    row[
                        "source_type"
                    ],
                    row[
                        "source_node"
                    ],
                )
            )

            nodes.add(
                (
                    row[
                        "target_type"
                    ],
                    row[
                        "target_node"
                    ],
                )
            )

        for node_type, _ in nodes:
            node_types[
                node_type
            ] += 1

        return {
            "graph_version":
                GRAPH_VERSION,

            "edge_count":
                len(records),

            "node_count":
                len(nodes),

            "node_types":
                dict(
                    sorted(
                        node_types.items()
                    )
                ),

            "relationship_counts":
                dict(
                    sorted(
                        relationship_counts.items()
                    )
                ),

            "channel_counts":
                dict(
                    sorted(
                        channel_counts.items()
                    )
                ),

            "records":
                records,
        }
