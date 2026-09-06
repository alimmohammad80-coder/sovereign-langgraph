from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


GLEIF_BASE = "https://api.gleif.org/api/v1"


class GLEIFCollector:
    """GLEIF LEI identity and relationship collector."""

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = requests.get(
            f"{GLEIF_BASE}{path}",
            params=params or {},
            headers={"Accept": "application/vnd.api+json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected GLEIF response")
        return data

    @staticmethod
    def _normalize_record(item: Dict[str, Any]) -> Dict[str, Any]:
        attributes = item.get("attributes") or {}
        entity = attributes.get("entity") or {}
        legal_name = (entity.get("legalName") or {}).get("name")
        jurisdiction = entity.get("jurisdiction")
        legal_address = entity.get("legalAddress") or {}
        headquarters = entity.get("headquartersAddress") or {}
        registration = attributes.get("registration") or {}

        return {
            "provider": "gleif",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "lei": attributes.get("lei") or item.get("id"),
            "legal_name": legal_name,
            "jurisdiction": jurisdiction,
            "legal_form": (entity.get("legalForm") or {}).get("id"),
            "entity_status": entity.get("status"),
            "registration_status": registration.get("status"),
            "legal_address": {
                "country": legal_address.get("country"),
                "region": legal_address.get("region"),
                "city": legal_address.get("city"),
                "postal_code": legal_address.get("postalCode"),
                "address_lines": legal_address.get("addressLines") or [],
            },
            "headquarters_address": {
                "country": headquarters.get("country"),
                "region": headquarters.get("region"),
                "city": headquarters.get("city"),
                "postal_code": headquarters.get("postalCode"),
                "address_lines": headquarters.get("addressLines") or [],
            },
            "other_names": [
                entry.get("name") for entry in (entity.get("otherNames") or [])
                if isinstance(entry, dict) and entry.get("name")
            ],
            "source_url": f"{GLEIF_BASE}/lei-records/{attributes.get('lei') or item.get('id')}",
        }

    def get_lei(self, lei: str) -> Dict[str, Any]:
        raw = self._get(f"/lei-records/{lei.strip().upper()}")
        item = raw.get("data")
        if not isinstance(item, dict):
            raise ValueError("GLEIF LEI record not found")
        return self._normalize_record(item)

    def search_by_name(
        self,
        legal_name: str,
        country: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "filter[entity.names]": legal_name.strip(),
            "page[size]": max(1, min(100, int(limit))),
        }
        if country:
            params["filter[entity.legalAddress.country]"] = country.strip().upper()

        raw = self._get("/lei-records", params=params)
        data = raw.get("data") or []
        if not isinstance(data, list):
            return []
        return [self._normalize_record(item) for item in data if isinstance(item, dict)]

    def best_match(
        self,
        legal_name: str,
        country: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        candidates = self.search_by_name(legal_name, country=country, limit=20)
        if not candidates:
            return None

        needle = legal_name.strip().casefold()
        exact = [item for item in candidates if str(item.get("legal_name") or "").casefold() == needle]
        if exact:
            return exact[0]
        return candidates[0]

    def relationships(self, lei: str) -> Dict[str, Any]:
        normalized = lei.strip().upper()
        raw = self._get(
            "/relationship-records",
            params={
                "filter[relationship.startNode]": normalized,
                "page[size]": 100,
            },
        )
        relationships: List[Dict[str, Any]] = []
        for item in raw.get("data") or []:
            if not isinstance(item, dict):
                continue
            attributes = item.get("attributes") or {}
            relationship = attributes.get("relationship") or {}
            start = relationship.get("startNode") or {}
            end = relationship.get("endNode") or {}
            relationships.append({
                "relationship_id": item.get("id"),
                "relationship_type": relationship.get("type"),
                "start_node": start.get("nodeId"),
                "start_node_type": start.get("nodeIdType"),
                "end_node": end.get("nodeId"),
                "end_node_type": end.get("nodeIdType"),
                "status": (attributes.get("registration") or {}).get("status"),
            })
        return {
            "provider": "gleif",
            "lei": normalized,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "relationships": relationships,
            "count": len(relationships),
        }
