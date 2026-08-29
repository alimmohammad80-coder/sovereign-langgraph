from __future__ import annotations

import re
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


class CanonicalConflictResolver:
    """
    Resolve two states to a canonical conflict episode without modifying
    source records.

    Resolution uses:
      - canonical episode state participants
      - border dyads
      - disputes
      - territories
      - frozen conflicts
      - country aliases

    No country-pair special cases are permitted.
    """

    MATCH_THRESHOLD = 80.0
    AMBIGUITY_MARGIN = 7.5

    def __init__(self) -> None:
        self.db = get_supabase_client()

        self.countries = self._load(
            "conflict_countries"
        )
        self.aliases = self._load(
            "conflict_country_aliases"
        )
        self.episodes = self._load(
            "conflict_canonical_episodes"
        )
        self.dyads = self._load(
            "conflict_border_dyads"
        )
        self.disputes = self._load(
            "conflict_disputes"
        )
        self.territories = self._load(
            "conflict_territories"
        )
        self.frozen_conflicts = self._load(
            "conflict_frozen_conflicts"
        )

        self.country_lookup = (
            self._build_country_lookup()
        )

        self.dyad_by_id = {
            str(row["dyad_id"]): row
            for row in self.dyads
            if row.get("dyad_id")
        }

        self.territory_by_id = {
            str(row["territory_id"]): row
            for row in self.territories
            if row.get("territory_id")
        }

        self.dispute_by_id = {
            str(row["dispute_id"]): row
            for row in self.disputes
            if row.get("dispute_id")
        }

    def _load(
        self,
        table: str,
    ) -> list[dict[str, Any]]:
        try:
            return (
                self.db.table(table)
                .select("*")
                .execute()
                .data
                or []
            )
        except Exception:
            return []

    @staticmethod
    def _norm(
        value: Any,
    ) -> str:
        return re.sub(
            r"[^a-z0-9]+",
            " ",
            str(value or "")
            .strip()
            .lower(),
        ).strip()

    @staticmethod
    def _iso_set(
        values: Any,
    ) -> set[str]:

        if not isinstance(
            values,
            list,
        ):
            return set()

        return {
            str(value)
            .strip()
            .upper()
            for value in values
            if value
        }

    def _build_country_lookup(
        self,
    ) -> dict[str, str]:

        lookup: dict[str, str] = {}

        for row in self.countries:
            iso3 = str(
                row.get("iso3")
                or ""
            ).strip().upper()

            if not iso3:
                continue

            values = [
                iso3,
                row.get("iso2"),
                row.get("name"),
                row.get(
                    "official_name"
                ),
            ]

            for value in values:
                normalized = (
                    self._norm(value)
                )

                if normalized:
                    lookup[
                        normalized
                    ] = iso3

        for row in self.aliases:

            iso3 = str(
                row.get("iso3")
                or row.get(
                    "country_iso3"
                )
                or ""
            ).strip().upper()

            alias = self._norm(
                row.get("alias")
                or row.get(
                    "country_alias"
                )
            )

            if iso3 and alias:
                lookup[alias] = iso3

        return lookup

    def normalize_participant(
        self,
        value: str,
    ) -> str:

        normalized = self._norm(
            value
        )

        iso3 = (
            self.country_lookup
            .get(normalized)
        )

        if not iso3:
            raise ValueError(
                "Unknown conflict participant: "
                f"{value}"
            )

        return iso3

    @staticmethod
    def _pair(
        a: str,
        b: str,
    ) -> tuple[str, str]:
        return tuple(
            sorted(
                (
                    a.upper(),
                    b.upper(),
                )
            )
        )

    def _dyad_pair(
        self,
        row: dict[str, Any],
    ) -> tuple[str, str] | None:

        a = str(
            row.get(
                "country_a_iso3"
            )
            or ""
        ).upper()

        b = str(
            row.get(
                "country_b_iso3"
            )
            or ""
        ).upper()

        if not a or not b:
            return None

        return self._pair(
            a,
            b,
        )

    def _territory_labels(
        self,
        territory_id: Any,
    ) -> set[str]:

        row = (
            self.territory_by_id
            .get(
                str(
                    territory_id
                    or ""
                )
            )
        )

        if not row:
            return set()

        result = set()

        for value in (
            row.get("name"),
            row.get(
                "territory_id"
            ),
            row.get(
                "geometry_ref"
            ),
        ):
            normalized = (
                self._norm(value)
            )

            if normalized:
                result.add(
                    normalized
                )

        return result

    def _episode_labels(
        self,
        episode: dict[str, Any],
    ) -> set[str]:

        values: list[Any] = []

        territories = (
            episode.get(
                "territories"
            )
            or []
        )

        locations = (
            episode.get(
                "location"
            )
            or []
        )

        if not isinstance(
            territories,
            list,
        ):
            territories = [
                territories
            ]

        if not isinstance(
            locations,
            list,
        ):
            locations = [
                locations
            ]

        values.extend(
            territories
        )
        values.extend(
            locations
        )

        return {
            self._norm(value)
            for value in values
            if self._norm(value)
        }

    @staticmethod
    def _labels_overlap(
        left: set[str],
        right: set[str],
    ) -> bool:

        for a in left:
            for b in right:

                if (
                    a == b
                    or a in b
                    or b in a
                ):
                    return True

        return False

    def _relationship_contexts(
        self,
        pair: tuple[str, str],
    ) -> list[dict[str, Any]]:

        requested = set(pair)
        contexts: list[
            dict[str, Any]
        ] = []

        #
        # 1. Border dyads
        #
        for row in self.dyads:

            if not row.get(
                "active",
                True,
            ):
                continue

            if (
                self._dyad_pair(row)
                != pair
            ):
                continue

            labels = set()

            for value in (
                row.get(
                    "dispute_name"
                ),
                row.get(
                    "dispute_ref"
                ),
            ):
                normalized = (
                    self._norm(value)
                )

                if normalized:
                    labels.add(
                        normalized
                    )

            contexts.append(
                {
                    "method":
                        "border_dyad",

                    "score":
                        75.0,

                    "labels":
                        labels,
                }
            )

        #
        # 2. Disputes
        #
        for row in self.disputes:

            if not row.get(
                "active",
                True,
            ):
                continue

            claimants = (
                self._iso_set(
                    row.get(
                        "claimant_iso3"
                    )
                )
            )

            dyad = (
                self.dyad_by_id
                .get(
                    str(
                        row.get(
                            "primary_dyad_id"
                        )
                        or ""
                    )
                )
            )

            dyad_pair = (
                self._dyad_pair(
                    dyad
                )
                if dyad
                else None
            )

            if not (
                requested
                .issubset(
                    claimants
                )
                or dyad_pair
                == pair
            ):
                continue

            labels = set()

            name = self._norm(
                row.get("name")
            )

            if name:
                labels.add(
                    name
                )

            labels.update(
                self._territory_labels(
                    row.get(
                        "territory_id"
                    )
                )
            )

            contexts.append(
                {
                    "method":
                        "territorial_dispute",

                    "score":
                        90.0,

                    "labels":
                        labels,
                }
            )

        #
        # 3. Territories
        #
        for row in self.territories:

            if not row.get(
                "active",
                True,
            ):
                continue

            claimants = (
                self._iso_set(
                    row.get(
                        "claimants"
                    )
                )
            )

            de_jure = str(
                row.get(
                    "de_jure_iso3"
                )
                or ""
            ).upper()

            if de_jure:
                claimants.add(
                    de_jure
                )

            if not requested.issubset(
                claimants
            ):
                continue

            labels = set()

            for value in (
                row.get("name"),
                row.get(
                    "territory_id"
                ),
                row.get(
                    "geometry_ref"
                ),
            ):
                normalized = (
                    self._norm(value)
                )

                if normalized:
                    labels.add(
                        normalized
                    )

            contexts.append(
                {
                    "method":
                        "territory_relationship",

                    "score":
                        90.0,

                    "labels":
                        labels,
                }
            )

        #
        # 4. Frozen conflicts
        #
        for row in self.frozen_conflicts:

            if not row.get(
                "active",
                True,
            ):
                continue

            parties = (
                self._iso_set(
                    row.get(
                        "parties"
                    )
                )
            )

            dyad = (
                self.dyad_by_id
                .get(
                    str(
                        row.get(
                            "primary_dyad_id"
                        )
                        or ""
                    )
                )
            )

            dyad_pair = (
                self._dyad_pair(
                    dyad
                )
                if dyad
                else None
            )

            dispute = (
                self.dispute_by_id
                .get(
                    str(
                        row.get(
                            "dispute_id"
                        )
                        or ""
                    )
                )
            )

            dispute_claimants = (
                self._iso_set(
                    dispute.get(
                        "claimant_iso3"
                    )
                )
                if dispute
                else set()
            )

            if not (
                requested
                .issubset(
                    parties
                )
                or dyad_pair
                == pair
                or requested
                .issubset(
                    dispute_claimants
                )
            ):
                continue

            labels = set()

            name = self._norm(
                row.get("name")
            )

            if name:
                labels.add(
                    name
                )

            labels.update(
                self._territory_labels(
                    row.get(
                        "territory_id"
                    )
                )
            )

            if dispute:
                dispute_name = (
                    self._norm(
                        dispute.get(
                            "name"
                        )
                    )
                )

                if dispute_name:
                    labels.add(
                        dispute_name
                    )

            contexts.append(
                {
                    "method":
                        "frozen_conflict",

                    "score":
                        95.0,

                    "labels":
                        labels,
                }
            )

        return contexts

    def _candidate(
        self,
        *,
        episode: dict[str, Any],
        pair: tuple[str, str],
        contexts: list[
            dict[str, Any]
        ],
        territory: str | None,
    ) -> dict[str, Any] | None:

        participants = (
            self._iso_set(
                episode.get(
                    "state_participants"
                )
            )
        )

        requested = set(pair)

        labels = (
            self._episode_labels(
                episode
            )
        )

        score = 0.0
        methods: list[str] = []

        #
        # Strongest possible match:
        # both states already exist
        # in canonical source coding.
        #
        if requested.issubset(
            participants
        ):
            score = 100.0

            methods.append(
                "exact_state_participants"
            )

        else:

            #
            # For indirect resolution,
            # at least one of the
            # requested states must be
            # part of the episode.
            #
            if not (
                participants
                .intersection(
                    requested
                )
            ):
                return None

            best_score = 0.0
            best_method = None

            for context in contexts:

                context_score = float(
                    context[
                        "score"
                    ]
                )

                context_labels = (
                    context.get(
                        "labels"
                    )
                    or set()
                )

                if (
                    context_labels
                    and labels
                    and self._labels_overlap(
                        context_labels,
                        labels,
                    )
                ):
                    context_score += (
                        15.0
                    )

                if (
                    context_score
                    > best_score
                ):
                    best_score = (
                        context_score
                    )

                    best_method = (
                        context[
                            "method"
                        ]
                    )

            if not best_method:
                return None

            score = best_score
            methods.append(
                best_method
            )

        #
        # Optional user-selected
        # territory improves ranking.
        #
        requested_territory = (
            self._norm(
                territory
            )
        )

        if requested_territory:

            if self._labels_overlap(
                {
                    requested_territory
                },
                labels,
            ):
                score += 20.0

                methods.append(
                    "territory_match"
                )

            else:
                score -= 20.0

        #
        # Small deterministic recency
        # tie-breaker only.
        #
        end_year = episode.get(
            "end_year"
        )

        if isinstance(
            end_year,
            int,
        ):
            if end_year >= 2020:
                score += 3.0

            elif end_year >= 2000:
                score += 1.0

        episode_territories = (
            episode.get(
                "territories"
            )
            or []
        )

        if not isinstance(
            episode_territories,
            list,
        ):
            episode_territories = [
                episode_territories
            ]

        territory_name = (
            str(
                episode_territories[
                    0
                ]
            )
            if episode_territories
            else None
        )

        return {
            "conflict_id":
                int(
                    episode[
                        "conflict_id"
                    ]
                ),

            "canonical_episode_id":
                str(
                    episode.get(
                        "id"
                    )
                    or ""
                ),

            "territory":
                territory_name,

            "source_participants":
                sorted(
                    participants
                ),

            "score":
                round(
                    score,
                    2,
                ),

            "resolution_method":
                "+".join(
                    methods
                ),
        }

    def resolve(
        self,
        *,
        participant_a: str,
        participant_b: str,
        territory: str | None = None,
    ) -> dict[str, Any]:

        a = self.normalize_participant(
            participant_a
        )

        b = self.normalize_participant(
            participant_b
        )

        if a == b:
            raise ValueError(
                "Participants must resolve "
                "to two different states."
            )

        pair = self._pair(
            a,
            b,
        )

        contexts = (
            self._relationship_contexts(
                pair
            )
        )

        candidates: list[
            dict[str, Any]
        ] = []

        for episode in self.episodes:

            if not episode.get(
                "active",
                True,
            ):
                continue

            candidate = (
                self._candidate(
                    episode=episode,
                    pair=pair,
                    contexts=contexts,
                    territory=territory,
                )
            )

            if candidate:
                candidates.append(
                    candidate
                )

        candidates.sort(
            key=lambda row: (
                float(
                    row["score"]
                ),
                int(
                    row["conflict_id"]
                ),
            ),
            reverse=True,
        )

        qualified = [
            row
            for row
            in candidates
            if float(
                row["score"]
            )
            >= self.MATCH_THRESHOLD
        ]

        if not qualified:
            return {
                "matched":
                    False,

                "requires_selection":
                    False,

                "participants":
                    list(pair),

                "alternatives":
                    [],
            }

        top = qualified[0]

        close = [
            row
            for row
            in qualified[1:]
            if (
                float(
                    top["score"]
                )
                - float(
                    row["score"]
                )
                <= self.AMBIGUITY_MARGIN
            )
        ]

        if (
            close
            and not territory
        ):
            return {
                "matched":
                    False,

                "requires_selection":
                    True,

                "participants":
                    list(pair),

                "alternatives":
                    [
                        top,
                        *close,
                    ],
            }

        confidence = min(
            1.0,
            float(
                top["score"]
            )
            / 100.0,
        )

        return {
            "matched":
                True,

            "requires_selection":
                False,

            "conflict_id":
                top[
                    "conflict_id"
                ],

            "canonical_episode_id":
                top[
                    "canonical_episode_id"
                ],

            "territory":
                top[
                    "territory"
                ],

            "participants":
                list(pair),

            "resolution_method":
                top[
                    "resolution_method"
                ],

            "confidence":
                round(
                    confidence,
                    4,
                ),

            "alternatives":
                close,
        }
