from __future__ import annotations

from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.conflict_entity_resolver import (
    ConflictEntityResolver,
)


class ConflictEventMatcher:
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.resolver = (
            ConflictEntityResolver()
        )

    def _episodes(
        self,
    ) -> list[dict[str, Any]]:
        return (
            self.db.table(
                "conflict_canonical_episodes"
            )
            .select("*")
            .execute()
            .data
            or []
        )

    @staticmethod
    def _participants(
        episode: dict[str, Any],
    ) -> set[str]:

        values = (
            episode.get("state_participants")
            or []
        )

        return {
            str(x).upper()
            for x in values
            if x
        }

    def match(
        self,
        *,
        title: str | None,
        summary: str | None,
    ) -> dict[str, Any]:

        entities = self.resolver.resolve(
            title=title,
            summary=summary,
        )

        event_states = set(
            entities[
                "country_iso3"
            ]
        )

        candidates = []

        event_territory_ids = {
            str(x.get("territory_id") or "").upper()
            for x in entities.get("territories", [])
            if x.get("territory_id")
        }

        event_territory_names = {
            str(x.get("name") or "").strip().lower()
            for x in entities.get("territories", [])
            if x.get("name")
        }

        raw_text = (
            f"{title or ''} {summary or ''}"
            .strip()
            .lower()
        )

        for episode in self._episodes():

            participants = self._participants(
                episode
            )

            overlap = (
                event_states
                & participants
            )

            episode_territories = {
                str(x).strip().lower()
                for x in (
                    episode.get("territories")
                    or []
                )
                if x
            }

            territory_overlap = (
                event_territory_names
                & episode_territories
            )

            #
            # Territory text fallback.
            # Useful when the entity resolver recognizes
            # "Kashmir" in plain text but not an exact
            # conflict_territories record.
            #
            territory_text_match = False

            for territory in episode_territories:
                if (
                    territory
                    and territory in raw_text
                ):
                    territory_text_match = True
                    break

            #
            # Require at least one substantive relation.
            #
            if (
                not overlap
                and not territory_overlap
                and not territory_text_match
            ):
                continue

            score = 0

            #
            # Country evidence.
            #
            score += (
                len(overlap)
                * 2
            )

            #
            # Exact full-dyad match is highly informative.
            #
            if (
                len(event_states) >= 2
                and event_states == participants
            ):
                score += 8

            elif (
                len(event_states) >= 2
                and event_states <= participants
            ):
                score += 5

            #
            # Territory evidence should dominate
            # ambiguous single-country matches.
            #
            if territory_overlap:
                score += (
                    10
                    * len(territory_overlap)
                )

            elif territory_text_match:
                score += 8

            #
            # Penalize episodes that contain unrelated
            # participants when the article clearly names
            # a different dyad.
            #
            if (
                len(event_states) >= 2
                and not event_states <= participants
            ):
                score -= 6

            candidates.append(
                {
                    "conflict_id":
                        episode.get(
                            "conflict_id"
                        ),

                    "canonical_episode_id":
                        episode.get(
                            "id"
                        ),

                    "participants":
                        sorted(
                            participants
                        ),

                    "matched_states":
                        sorted(
                            overlap
                        ),

                    "matched_territories":
                        sorted(
                            territory_overlap
                        ),

                    "territory_text_match":
                        territory_text_match,

                    "match_score":
                        score,
                }
            )

        candidates.sort(
            key=lambda x: (
                x[
                    "match_score"
                ],
                len(
                    x[
                        "matched_states"
                    ]
                ),
            ),
            reverse=True,
        )

        best = (
            candidates[0]
            if candidates
            else None
        )

        return {
            "entities":
                entities,

            "matched":
                best is not None,

            "best_match":
                best,

            "candidate_count":
                len(candidates),

            "candidates":
                candidates[:10],
        }
