from __future__ import annotations

import os
from typing import Any

from .base import BaseCollector, CollectorError


class MispCollector(BaseCollector):
    source_name = "MISP"

    async def collect_events(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        limit: int = 100,
        published_only: bool = True,
    ) -> dict[str, Any]:
        key = api_key or os.getenv("MISP_API_KEY")
        if not key:
            raise CollectorError("MISP API key is not configured")

        url = f"{base_url.rstrip('/')}/events/restSearch"
        payload = await self.post_json(
            url,
            payload={
                "returnFormat": "json",
                "limit": max(1, min(limit, 1000)),
                "published": published_only,
            },
            headers={"Authorization": key},
        )
        response = payload.get("response", payload)
        events = response if isinstance(response, list) else response.get("Event", [])
        if isinstance(events, dict):
            events = [events]

        collected_at = self.collected_at()
        records = []
        for wrapper in events[: max(1, min(limit, 1000))]:
            event = wrapper.get("Event", wrapper) if isinstance(wrapper, dict) else {}
            event_id = str(event.get("uuid") or event.get("id") or "")
            normalized_attributes = []
            for attr in event.get("Attribute") or []:
                normalized_attributes.append({
                    "uuid": attr.get("uuid"),
                    "type": attr.get("type"),
                    "category": attr.get("category"),
                    "value": attr.get("value"),
                    "to_ids": attr.get("to_ids"),
                    "comment": attr.get("comment"),
                    "timestamp": attr.get("timestamp"),
                    "tags": [tag.get("name") for tag in attr.get("Tag", []) if tag.get("name")],
                })

            records.append({
                "source": "misp",
                "record_type": "misp_event",
                "source_record_id": event_id,
                "event_id": event.get("id"),
                "uuid": event.get("uuid"),
                "info": event.get("info"),
                "date": event.get("date"),
                "timestamp": event.get("timestamp"),
                "published": event.get("published"),
                "threat_level_id": event.get("threat_level_id"),
                "analysis": event.get("analysis"),
                "distribution": event.get("distribution"),
                "orgc": event.get("Orgc"),
                "tags": [tag.get("name") for tag in event.get("Tag", []) if tag.get("name")],
                "attributes": normalized_attributes,
                "provenance": {
                    "source_name": self.source_name,
                    "source_type": "misp_threat_intelligence_platform",
                    "source_url": base_url,
                    "publisher": (event.get("Orgc") or {}).get("name"),
                    "collected_at": collected_at.isoformat(),
                    "source_record_id": event_id,
                    "retrieval_method": "misp_rest_search_post",
                    "content_hash": self.stable_hash(event),
                },
            })
        return {"source": "misp", "count": len(records), "records": records}

    def normalize_event(self, event: dict[str, Any], *, source_url: str | None = None) -> dict[str, Any]:
        wrapper = {"Event": event}
        collected_at = self.collected_at()
        event_id = str(event.get("uuid") or event.get("id") or "")
        attributes = [{
            "uuid": a.get("uuid"), "type": a.get("type"), "category": a.get("category"),
            "value": a.get("value"), "to_ids": a.get("to_ids"), "comment": a.get("comment"),
            "timestamp": a.get("timestamp"),
        } for a in event.get("Attribute", [])]
        return {
            "source": "misp",
            "record_type": "misp_event",
            "source_record_id": event_id,
            "uuid": event.get("uuid"),
            "info": event.get("info"),
            "attributes": attributes,
            "provenance": {
                "source_name": self.source_name,
                "source_type": "misp_threat_intelligence_platform",
                "source_url": source_url,
                "collected_at": collected_at.isoformat(),
                "source_record_id": event_id,
                "retrieval_method": "misp_event_normalization",
                "content_hash": self.stable_hash(wrapper),
            },
        }
