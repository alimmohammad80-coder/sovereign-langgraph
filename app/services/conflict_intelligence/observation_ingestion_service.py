from __future__ import annotations

import hashlib
import json
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


class ConflictObservationIngestionService:

    def __init__(self):
        self.db = get_supabase_client()
        self.alias_lookup = self._load_aliases()

    def _load_aliases(self) -> dict[str, str]:

        rows = (
            self.db.table("conflict_country_aliases")
            .select("alias,iso3")
            .eq("active", True)
            .execute()
            .data
            or []
        )

        lookup: dict[str, str] = {}

        for row in rows:
            alias = str(row["alias"]).strip().lower()
            lookup[alias] = row["iso3"]

        return lookup

    def _resolve_country(
        self,
        country: str | None,
        country_iso3: str | None,
    ) -> str | None:

        if country_iso3:
            iso3 = country_iso3.strip().upper()

            result = (
                self.db.table("conflict_countries")
                .select("iso3")
                .eq("iso3", iso3)
                .limit(1)
                .execute()
                .data
                or []
            )

            if not result:
                raise ValueError(
                    f"Unknown country ISO3: {iso3}"
                )

            return iso3

        if not country:
            return None

        normalized = country.strip().lower()

        return self.alias_lookup.get(normalized)

    def _resolve_episode(
        self,
        conflict_id: int | None,
    ) -> tuple[int | None, str | None]:

        if conflict_id is None:
            return None, None

        rows = (
            self.db.table("conflict_canonical_episodes")
            .select("id,conflict_id")
            .eq("conflict_id", conflict_id)
            .limit(1)
            .execute()
            .data
            or []
        )

        if not rows:
            raise ValueError(
                f"Unknown canonical conflict_id: {conflict_id}"
            )

        return (
            int(rows[0]["conflict_id"]),
            str(rows[0]["id"]),
        )

    def _match_episode_by_states(
        self,
        state_iso3: list[str],
    ) -> tuple[int | None, str | None]:

        states = sorted({
            str(value).strip().upper()
            for value in state_iso3
            if value
        })

        if not states:
            return None, None

        rows = (
            self.db.table("conflict_canonical_episodes")
            .select(
                "id,conflict_id,"
                "state_participants,"
                "start_year,end_year"
            )
            .eq("active", True)
            .execute()
            .data
            or []
        )

        matches = []

        requested = set(states)

        for row in rows:

            participants = {
                str(value).strip().upper()
                for value in (
                    row.get("state_participants")
                    or []
                )
                if value
            }

            if requested.issubset(participants):
                matches.append(row)

        if len(matches) != 1:
            return None, None

        row = matches[0]

        return (
            int(row["conflict_id"]),
            str(row["id"]),
        )

    @staticmethod
    def _observation_key(
        *,
        observed_at: str,
        source: str,
        source_url: str | None,
        title: str | None,
        country_iso3: str | None,
        conflict_id: int | None,
        event_type: str,
    ) -> str:

        canonical = {
            "observed_at": observed_at,
            "source": source.strip().lower(),
            "source_url": source_url or "",
            "title": title or "",
            "country_iso3": country_iso3 or "",
            "conflict_id": conflict_id,
            "event_type": event_type.strip().lower(),
        }

        digest = hashlib.sha256(
            json.dumps(
                canonical,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:24]

        return f"COBS-{digest.upper()}"

    def ingest(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        observed_at = payload["observed_at"]

        if hasattr(observed_at, "isoformat"):
            observed_at = observed_at.isoformat()

        country_iso3 = self._resolve_country(
            payload.get("country"),
            payload.get("country_iso3"),
        )

        conflict_id, canonical_episode_id = (
            self._resolve_episode(
                payload.get("conflict_id")
            )
        )

        if conflict_id is None:

            candidate_states = list(
                payload.get("related_state_iso3")
                or []
            )

            if country_iso3:
                candidate_states.append(
                    country_iso3
                )

            (
                conflict_id,
                canonical_episode_id,
            ) = self._match_episode_by_states(
                candidate_states
            )

        observation_key = self._observation_key(
            observed_at=observed_at,
            source=payload["source"],
            source_url=payload.get("source_url"),
            title=payload.get("title"),
            country_iso3=country_iso3,
            conflict_id=conflict_id,
            event_type=payload["event_type"],
        )

        existing = (
            self.db.table("conflict_observations")
            .select("id,observation_key")
            .eq("observation_key", observation_key)
            .limit(1)
            .execute()
            .data
            or []
        )

        if existing:
            return {
                "observation_key": observation_key,
                "country_iso3": country_iso3,
                "conflict_id": conflict_id,
                "canonical_episode_id":
                    canonical_episode_id,
                "created": False,
            }

        if conflict_id is not None:
            unit_type = "episode"
            unit_id = str(conflict_id)

        elif country_iso3:
            unit_type = "country"
            unit_id = country_iso3

        else:
            unit_type = "episode"
            unit_id = "UNRESOLVED"

        confidence = payload.get("confidence")

        if confidence is None:
            confidence_grade = "unknown"
        elif confidence >= 80:
            confidence_grade = "high"
        elif confidence >= 60:
            confidence_grade = "medium"
        else:
            confidence_grade = "low"

        row = {
            "observation_key": observation_key,

            "unit_id": unit_id,
            "unit_type": unit_type,

            "observed_at": observed_at,

            "indicator_key": payload["event_type"],

            "value_text": payload.get("summary"),

            "value_json": payload.get(
                "observation_data"
            ) or {},

            "source": payload["source"],
            "source_url": payload.get("source_url"),
            "source_version":
                payload.get("source_version"),

            "confidence_grade": confidence_grade,
            "review_status": "validated",

            "country_iso3": country_iso3,
            "conflict_id": conflict_id,
            "canonical_episode_id":
                canonical_episode_id,

            "event_type": payload["event_type"],
            "title": payload.get("title"),
            "summary": payload.get("summary"),

            "severity": payload.get("severity"),

            "observation_data":
                payload.get("observation_data") or {},

            "active": True,
        }

        (
            self.db.table("conflict_observations")
            .insert(row)
            .execute()
        )

        return {
            "observation_key": observation_key,
            "country_iso3": country_iso3,
            "conflict_id": conflict_id,
            "canonical_episode_id":
                canonical_episode_id,
            "created": True,
        }
