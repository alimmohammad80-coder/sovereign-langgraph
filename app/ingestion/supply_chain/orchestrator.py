from __future__ import annotations

import asyncio
import math
import re
from typing import Any

from app.ingestion.collection_result import CollectionResult
from app.ingestion.supply_chain.collectors import (
    EIACollector,
    GDACSCollector,
    GDELTSupplyChainCollector,
    GLEIFCollector,
    OFACCollector,
    OfficialFeedCollector,
    PortWatchCollector,
    SECEdgarCollector,
    UNComtradeCollector,
    USGSEarthquakeCollector,
)
from app.ingestion.supply_chain.models import SupplyChainEvidence
from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _contains(text: str, candidate: str) -> bool:
    candidate = _normalized(candidate)
    if not candidate:
        return False
    if len(candidate) <= 4:
        return bool(re.search(rf"\b{re.escape(candidate)}\b", text))
    return candidate in text


def _haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius = 6371.0
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a)
        * math.cos(lat_b)
        * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


class SupplyChainEvidenceRepository:
    def __init__(self) -> None:
        self.db = get_supabase_client()

    def entity_registry(self) -> dict[str, list[dict[str, Any]]]:
        registry: dict[str, list[dict[str, Any]]] = {
            "companies": [],
            "ports": [],
            "chokepoints": [],
            "commodities": [],
            "corridors": [],
        }
        queries = (
            ("companies", "sc_companies", "company_name"),
            (
                "ports",
                "sc_master_ports",
                "port_name,latitude,longitude,iso3",
            ),
            ("chokepoints", "sc_chokepoints", "name"),
            (
                "commodities",
                "sc_commodity_company_exposure",
                "commodity",
            ),
            (
                "corridors",
                "sc_shipping_corridors",
                "corridor_name",
            ),
        )
        for key, table, columns in queries:
            try:
                registry[key] = (
                    self.db.table(table).select(columns).execute().data
                    or []
                )
            except Exception:
                registry[key] = []
        return registry

    def persist(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        events: list[dict[str, Any]] = []
        for row in records:
            evidence = SupplyChainEvidence(
                **{
                    key: value
                    for key, value in row.items()
                    if key != "content_hash"
                }
            )
            event = evidence.to_live_event_row()
            if event and event.get("url"):
                events.append(event)

        for start in range(0, len(records), 100):
            (
                self.db.table("sc_external_evidence")
                .upsert(
                    records[start : start + 100],
                    on_conflict="source,source_record_id",
                )
                .execute()
            )

        for start in range(0, len(events), 100):
            (
                self.db.table("sc_live_disruption_events")
                .upsert(
                    events[start : start + 100],
                    on_conflict="url",
                )
                .execute()
            )

        return len(records), len(events)


class SupplyChainIngestionOrchestrator:
    def __init__(self) -> None:
        collectors = [
            GDELTSupplyChainCollector(),
            PortWatchCollector(),
            GDACSCollector(),
            USGSEarthquakeCollector(),
            UNComtradeCollector(),
            EIACollector(),
            OFACCollector(),
            SECEdgarCollector(),
            GLEIFCollector(),
            OfficialFeedCollector(),
        ]
        self.collectors = {
            collector.source_key: collector
            for collector in collectors
        }
        self.repository = SupplyChainEvidenceRepository()

    def available_sources(self) -> list[str]:
        return list(self.collectors)

    def _match_entities(
        self,
        records: list[dict[str, Any]],
        registry: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        names = {
            "matched_company": sorted(
                (
                    str(row.get("company_name"))
                    for row in registry["companies"]
                    if row.get("company_name")
                ),
                key=len,
                reverse=True,
            ),
            "matched_port": sorted(
                (
                    str(row.get("port_name"))
                    for row in registry["ports"]
                    if row.get("port_name")
                ),
                key=len,
                reverse=True,
            ),
            "matched_chokepoint": sorted(
                (
                    str(row.get("name"))
                    for row in registry["chokepoints"]
                    if row.get("name")
                ),
                key=len,
                reverse=True,
            ),
            "matched_commodity": sorted(
                {
                    str(row.get("commodity"))
                    for row in registry["commodities"]
                    if row.get("commodity")
                },
                key=len,
                reverse=True,
            ),
            "matched_corridor": sorted(
                (
                    str(row.get("corridor_name"))
                    for row in registry["corridors"]
                    if row.get("corridor_name")
                ),
                key=len,
                reverse=True,
            ),
        }
        alias_map = {
            "TSMC": ["taiwan semiconductor manufacturing"],
            "Nvidia": ["nvda"],
            "Strait of Hormuz": ["hormuz"],
            "Bab el-Mandeb": ["bab al mandab", "red sea"],
            "Suez Canal": ["suez"],
            "Strait of Malacca": ["malacca"],
            "Port of Kaohsiung": ["kaohsiung port", "kaohsiung"],
        }

        for row in records:
            text = _normalized(
                " ".join(
                    str(row.get(key) or "")
                    for key in ("title", "summary", "url")
                )
            )
            for field, candidates in names.items():
                if row.get(field):
                    continue
                for candidate in candidates:
                    aliases = [candidate, *alias_map.get(candidate, [])]
                    if any(_contains(text, alias) for alias in aliases):
                        row[field] = candidate
                        break

            geometry = (row.get("raw_payload") or {}).get("geometry")
            coordinates = (
                geometry.get("coordinates")
                if isinstance(geometry, dict)
                else None
            )
            if (
                not row.get("matched_port")
                and isinstance(coordinates, list)
                and len(coordinates) >= 2
            ):
                try:
                    longitude = float(coordinates[0])
                    latitude = float(coordinates[1])
                except (TypeError, ValueError):
                    continue
                nearest: tuple[float, str] | None = None
                for port in registry["ports"]:
                    if (
                        port.get("latitude") is None
                        or port.get("longitude") is None
                    ):
                        continue
                    distance = _haversine_km(
                        latitude,
                        longitude,
                        float(port["latitude"]),
                        float(port["longitude"]),
                    )
                    if nearest is None or distance < nearest[0]:
                        nearest = (distance, str(port["port_name"]))
                if nearest and nearest[0] <= 250:
                    row["matched_port"] = nearest[1]
                    row["raw_payload"]["distance_to_port_km"] = round(
                        nearest[0],
                        1,
                    )
        return records

    async def run_source(
        self,
        source_key: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        key = source_key.upper()
        collector = self.collectors.get(key)
        if not collector:
            raise KeyError(f"Unknown Supply Chain source: {source_key}")

        try:
            records, result = await collector.collect(context or {})
            registry = await asyncio.to_thread(
                self.repository.entity_registry
            )
            matched = self._match_entities(records, registry)
            if matched:
                evidence_count, event_count = await asyncio.to_thread(
                    self.repository.persist,
                    matched,
                )
            else:
                evidence_count, event_count = 0, 0
            result.records_ingested = evidence_count
            result.metadata["live_events_upserted"] = event_count
        except Exception as exc:
            result = CollectionResult(
                source_key=key,
                success=False,
                errors=[f"{type(exc).__name__}: {exc}"],
            )
        result.complete()
        return result.to_dict()

    async def run_all(
        self,
        contexts: dict[str, dict[str, Any]] | None = None,
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        requested = [
            source.upper()
            for source in (sources or self.available_sources())
        ]
        jobs = {
            source: asyncio.create_task(
                self.run_source(
                    source,
                    (contexts or {}).get(source, {}),
                )
            )
            for source in requested
        }
        results = {
            source: await job
            for source, job in jobs.items()
        }
        return {
            "status": (
                "success"
                if all(item["success"] for item in results.values())
                else "partial"
            ),
            "sources": results,
            "records_collected": sum(
                item["records_collected"]
                for item in results.values()
            ),
            "records_ingested": sum(
                item["records_ingested"]
                for item in results.values()
            ),
        }


def build_supply_chain_orchestrator() -> SupplyChainIngestionOrchestrator:
    return SupplyChainIngestionOrchestrator()
