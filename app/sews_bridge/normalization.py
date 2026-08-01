import hashlib, json
from datetime import datetime, timezone

def _first(record, *keys):
    for key in keys:
        value = record.get(key)
        if value not in (None, "", []):
            return value
    return None

def _dt(value):
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)

def normalize_existing_record(*, source_key, raw_record, problem_key, country_iso3, region_key, query):
    record = raw_record.model_dump(mode="json") if hasattr(raw_record, "model_dump") else (
        raw_record if isinstance(raw_record, dict) else {"value": raw_record}
    )
    title = str(_first(record, "title", "name", "headline", "series_name", "indicator_name") or f"{source_key} intelligence record")
    text = str(_first(record, "raw_text", "summary", "description", "content", "snippet", "value") or title)
    url = _first(record, "canonical_url", "url", "link", "source_url")
    external_id = _first(record, "source_external_id", "id", "guid", "globaleventid", "series_id")
    identity = json.dumps({"source": source_key, "id": external_id, "url": url, "title": title, "problem": problem_key}, sort_keys=True, default=str)
    digest = hashlib.sha256(identity.encode()).hexdigest()
    return {
        "signal_key": f"BRIDGE-{source_key}-{digest[:32]}",
        "source_key": source_key,
        "source_external_id": str(external_id) if external_id is not None else digest,
        "canonical_url": str(url) if url else None,
        "title": title,
        "raw_text": text,
        "content_type": "application/json",
        "language_code": str(_first(record, "language_code", "language") or "en"),
        "published_at": _dt(_first(record, "published_at", "published", "date", "seendate", "updated_at")),
        "observed_at": _dt(_first(record, "observed_at", "timestamp", "date")),
        "collector_agent": "sews-existing-source-bridge",
        "country_iso3": _first(record, "country_iso3", "iso3", "country") or country_iso3,
        "region_key": _first(record, "region_key", "region") or region_key,
        "metadata": {
            "warning_problem_key": problem_key,
            "collection_query": query,
            "bridge_source": source_key,
            "existing_platform_record": record,
        },
    }
