from __future__ import annotations

import re
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


class ConflictEntityResolver:
    def __init__(self) -> None:
        self.db = get_supabase_client()

        self.countries = self._load(
            "conflict_countries"
        )

        self.aliases = self._load(
            "conflict_country_aliases"
        )

        self.territories = self._load(
            "conflict_territories"
        )

        self.disputes = self._load(
            "conflict_disputes"
        )

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
    def _text(
        title: str | None,
        summary: str | None,
    ) -> str:
        return (
            f"{title or ''} {summary or ''}"
            .strip()
            .lower()
        )

    @staticmethod
    def _contains(
        text: str,
        value: str,
    ) -> bool:
        value = value.strip().lower()

        if len(value) < 3:
            return False

        pattern = (
            r"(?<!\w)"
            + re.escape(value)
            + r"(?!\w)"
        )

        return bool(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        )

    def resolve(
        self,
        *,
        title: str | None,
        summary: str | None,
    ) -> dict[str, Any]:

        text = self._text(
            title,
            summary,
        )

        countries: dict[str, str] = {}

        for row in self.countries:
            iso3 = str(
                row.get("iso3")
                or row.get("country_iso3")
                or ""
            ).upper()

            name = str(
                row.get("name")
                or row.get("country_name")
                or ""
            )

            if (
                iso3
                and name
                and self._contains(
                    text,
                    name,
                )
            ):
                countries[
                    iso3
                ] = name

        for row in self.aliases:
            alias = str(
                row.get("alias")
                or row.get("country_alias")
                or ""
            )

            iso3 = str(
                row.get("iso3")
                or row.get("country_iso3")
                or ""
            ).upper()

            if (
                alias
                and iso3
                and self._contains(
                    text,
                    alias,
                )
            ):
                countries.setdefault(
                    iso3,
                    alias,
                )

        territories = []

        for row in self.territories:
            name = str(
                row.get("name")
                or ""
            )

            if (
                name
                and self._contains(
                    text,
                    name,
                )
            ):
                territories.append(
                    {
                        "territory_id":
                            row.get(
                                "territory_id"
                            ),
                        "name":
                            name,
                    }
                )

        disputes = []

        for row in self.disputes:
            name = str(
                row.get("name")
                or ""
            )

            if (
                name
                and self._contains(
                    text,
                    name,
                )
            ):
                disputes.append(
                    {
                        "dispute_id":
                            row.get(
                                "dispute_id"
                            ),
                        "name":
                            name,
                        "claimant_iso3":
                            row.get(
                                "claimant_iso3"
                            )
                            or [],
                    }
                )

        return {
            "countries":
                [
                    {
                        "iso3": iso3,
                        "name": name,
                    }
                    for iso3, name
                    in sorted(
                        countries.items()
                    )
                ],

            "country_iso3":
                sorted(
                    countries.keys()
                ),

            "territories":
                territories,

            "disputes":
                disputes,
        }
