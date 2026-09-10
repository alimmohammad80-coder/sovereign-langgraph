import hashlib
import json
from datetime import datetime, timezone
from supabase import Client


class SEWSBridgeRepository:
    def __init__(self, db: Client):
        self.db = db

    def _source_id(self, source_key: str) -> str:
        result = self.db.table("sews_sources").select("id").eq("source_key", source_key).limit(1).execute()
        if result.data:
            return result.data[0]["id"]
        source_types = {
            "GOOGLE_NEWS_RSS": "NEWS",
            "GDELT": "EVENT_DATA",
            "NEWSAPI": "NEWS",
            "WORLD_BANK": "ECONOMIC_DATA",
            "IMF": "ECONOMIC_DATA",
            "FRED": "FINANCIAL_DATA",
            "EIA": "ENERGY_DATA",
            "RELIEFWEB": "HUMANITARIAN_DATA",
            "OFAC": "SANCTIONS_DATA",
            "SEWS_ECONOMIC": "ECONOMIC_DATA",
            "SEWS_ENERGY": "ENERGY_DATA",
            "SEWS_CONFLICT": "EVENT_DATA",
            "SEWS_POLITICAL": "EVENT_DATA",
            "SEWS_TRADE_SANCTIONS": "SANCTIONS_DATA",
        }

        created = self.db.table("sews_sources").insert({
            "source_key": source_key,
            "name": source_key.replace("_", " ").title(),
            "source_type": source_types.get(source_key, "OPEN_SOURCE"),
            "active": True,
            "status": "ACTIVE",
            "metadata": {"managed_by": "sews-existing-source-bridge"},
        }).execute()
        if not created.data:
            raise RuntimeError(f"Could not create source row for {source_key}")
        return created.data[0]["id"]

    @staticmethod
    def _content_hash(payload) -> str:
        canonical = json.dumps(
            {
                "title": payload.get("title"),
                "raw_text": payload.get("raw_text"),
                "canonical_url": payload.get("canonical_url"),
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def persist_evidence(self, payload):
        source_id = self._source_id(payload["source_key"])
        content_hash = self._content_hash(payload)
        external_id = payload.get("source_external_id")

        # Deduplicate only inside the same source. Identical/syndicated content
        # from a second independent source is analytically valuable because it
        # contributes to corroboration and must not be discarded globally.
        existing = self.db.table("sews_raw_evidence").select("id").eq(
            "source_id", source_id
        )
        if external_id:
            existing = existing.eq("source_external_id", str(external_id))
        else:
            existing = existing.eq("content_hash", content_hash)
        existing_result = existing.limit(1).execute()
        if existing_result.data:
            return False, existing_result.data[0]["id"]

        row = {
            "evidence_key": payload["signal_key"],
            "source_id": source_id,
            "source_external_id": str(external_id) if external_id is not None else None,
            "canonical_url": payload["canonical_url"],
            "title": payload["title"],
            "raw_text": payload["raw_text"],
            "raw_payload": payload["metadata"].get("existing_platform_record"),
            "content_type": payload["content_type"],
            "content_hash": content_hash,
            "language_code": payload["language_code"],
            "published_at": payload["published_at"],
            "observed_at": payload["observed_at"],
            "collector_agent": payload["collector_agent"],
            "country_iso3": payload["country_iso3"],
            "region_key": payload["region_key"],
            "status": "RAW",
            "metadata": payload["metadata"],
        }
        result = self.db.table("sews_raw_evidence").insert(row).execute()
        if not result.data:
            raise RuntimeError("Evidence insert returned no row")

        # Keep source health meaningful for the operations UI. This is only a
        # successful-collection timestamp; source-level failures remain tracked
        # separately by their owning collectors.
        self.db.table("sews_sources").update({
            "last_success_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", source_id).execute()

        return True, result.data[0]["id"]
