from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


class EconomicPropagationBuilder:

    METHOD = "economic-ontology-derived"

    def __init__(self) -> None:
        self.db = get_supabase_client()

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

    def _edge(
        self,
        *,
        source_node: str,
        source_type: str,
        target_node: str,
        target_type: str,
        relationship: str,
        channel: str,
        transmission_weight: float,
        confidence: float,
    ) -> dict[str, Any]:

        return {
            "edge_key":
                self._edge_key(
                    source_node,
                    relationship,
                    target_node,
                ),

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
                channel,

            "transmission_weight":
                transmission_weight,

            "damping_factor":
                1.0,

            "confidence":
                confidence,

            "method":
                self.METHOD,

            "source":
                "Sovereign Intelligence conflict ontology",

            "source_version":
                "conflict-intelligence-ontology-v1",

            "active":
                True,

            "review_status":
                "validated",

            "last_reviewed":
                date.today().isoformat(),
        }

    def _countries(
        self,
    ) -> list[dict[str, Any]]:

        # Use the canonical conflict-country registry already
        # supporting the Conflict Intelligence ontology.
        rows = (
            self.db.table(
                "conflict_countries"
            )
            .select("*")
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        return rows

    @staticmethod
    def _iso3(
        row: dict[str, Any],
    ) -> str | None:

        for key in [
            "iso3",
            "country_iso3",
            "iso_alpha3",
        ]:

            value = row.get(
                key
            )

            if value:
                return str(
                    value
                ).upper()

        return None

    def build(
        self,
    ) -> dict[str, Any]:

        records = []

        countries = self._countries()

        skipped = 0

        for row in countries:

            iso3 = self._iso3(
                row
            )

            if not iso3:
                skipped += 1
                continue

            macro = (
                f"MACRO-{iso3}"
            )

            sovereign = (
                f"SOVEREIGN-{iso3}"
            )

            fx = (
                f"FX-{iso3}"
            )

            # Conflict/geopolitical shock enters the
            # country's domestic macro system.
            records.append(
                self._edge(
                    source_node=iso3,
                    source_type="country",
                    target_node=macro,
                    target_type="macro",
                    relationship="affects_domestic_macro",
                    channel="domestic_macro",
                    transmission_weight=0.70,
                    confidence=85,
                )
            )

            # Domestic macro stress can transmit to
            # sovereign financing conditions.
            records.append(
                self._edge(
                    source_node=macro,
                    source_type="macro",
                    target_node=sovereign,
                    target_type="sovereign",
                    relationship="affects_sovereign_risk",
                    channel="sovereign_fx",
                    transmission_weight=0.65,
                    confidence=80,
                )
            )

            # Domestic macro stress can transmit into
            # currency pressure.
            records.append(
                self._edge(
                    source_node=macro,
                    source_type="macro",
                    target_node=fx,
                    target_type="fx",
                    relationship="affects_fx",
                    channel="sovereign_fx",
                    transmission_weight=0.60,
                    confidence=80,
                )
            )

            # Sovereign stress can reinforce FX pressure.
            records.append(
                self._edge(
                    source_node=sovereign,
                    source_type="sovereign",
                    target_node=fx,
                    target_type="fx",
                    relationship="sovereign_to_fx",
                    channel="sovereign_fx",
                    transmission_weight=0.55,
                    confidence=75,
                )
            )

        return {
            "builder":
                "economic-propagation",

            "country_count":
                len(countries),

            "skipped_country_count":
                skipped,

            "edge_count":
                len(records),

            "records":
                records,
        }
