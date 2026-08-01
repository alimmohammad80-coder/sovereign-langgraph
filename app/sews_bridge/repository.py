import hashlib
from supabase import Client

class SEWSBridgeRepository:
    def __init__(self, db: Client):
        self.db = db

    def _source_id(self, source_key: str) -> str:
        result = self.db.table("sews_sources").select("id").eq("source_key", source_key).limit(1).execute()
        if result.data:
            return result.data[0]["id"]
        created = self.db.table("sews_sources").insert({
            "source_key": source_key,
            "name": source_key.replace("_", " ").title(),
            "active": True,
            "metadata": {"managed_by": "sews-existing-source-bridge"},
        }).execute()
        if not created.data:
            raise RuntimeError(f"Could not create source row for {source_key}")
        return created.data[0]["id"]

    def persist_evidence(self, payload):
        source_id = self._source_id(payload["source_key"])
        content_hash = hashlib.sha256(payload["raw_text"].encode()).hexdigest()
        existing = self.db.table("sews_raw_evidence").select("id").eq("content_hash", content_hash).limit(1).execute()
        if existing.data:
            return False, existing.data[0]["id"]
        row = {
            "evidence_key": payload["signal_key"],
            "source_id": source_id,
            "source_external_id": payload["source_external_id"],
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
        return True, result.data[0]["id"]
