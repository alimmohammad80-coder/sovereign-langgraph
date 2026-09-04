from __future__ import annotations

from typing import Any

from .base import BaseCollector, CollectorError


class StixBundleAdapter(BaseCollector):
    source_name = "STIX 2.x"

    def normalize_bundle(self, bundle: dict[str, Any], *, source_name: str, source_url: str | None = None) -> dict[str, Any]:
        if bundle.get("type") != "bundle" or not isinstance(bundle.get("objects"), list):
            raise CollectorError("payload is not a valid STIX bundle")
        collected_at = self.collected_at()
        records = []
        for obj in bundle["objects"]:
            if not isinstance(obj, dict) or not obj.get("type") or not obj.get("id"):
                continue
            records.append({
                "source": source_name,
                "record_type": obj.get("type"),
                "source_record_id": obj.get("id"),
                "name": obj.get("name"),
                "created": obj.get("created"),
                "modified": obj.get("modified"),
                "raw_stix": obj,
                "provenance": {
                    "source_name": source_name,
                    "source_type": "stix_bundle",
                    "source_url": source_url,
                    "collected_at": collected_at.isoformat(),
                    "source_record_id": obj.get("id"),
                    "retrieval_method": "stix_bundle_normalization",
                    "content_hash": self.stable_hash(obj),
                },
            })
        return {"source": source_name, "count": len(records), "records": records}


class TaxiiCollectionCollector(BaseCollector):
    source_name = "TAXII 2.x"

    async def collect_objects(
        self,
        *,
        objects_url: str,
        bearer_token: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/taxii+json;version=2.1"}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        payload = await self.get_json(objects_url, params={"limit": max(1, min(limit, 5000))}, headers=headers)
        # TAXII envelopes contain an objects array; convert to a STIX bundle for the shared adapter.
        bundle = {"type": "bundle", "objects": payload.get("objects", [])}
        return StixBundleAdapter().normalize_bundle(bundle, source_name="taxii", source_url=objects_url)
