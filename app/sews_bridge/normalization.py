import hashlib, json
from datetime import datetime, timezone


SOURCE_ALIASES = {
    "eia": "EIA",
    "u.s. energy information administration": "EIA",
    "us energy information administration": "EIA",
    "fred": "FRED",
    "federal reserve economic data": "FRED",
    "world bank": "WORLD_BANK",
    "world bank open data": "WORLD_BANK",
    "imf": "IMF",
    "international monetary fund": "IMF",
    "ofac": "OFAC",
    "office of foreign assets control": "OFAC",
    "reliefweb": "RELIEFWEB",
    "google news": "GOOGLE_NEWS_RSS",
    "google news rss": "GOOGLE_NEWS_RSS",
    "gdelt": "GDELT",
    "newsapi": "NEWSAPI",
}


def _first(record, *keys):
    for key in keys:
        value = record.get(key)
        if value not in (None, "", []):
            return value
    return None


def _dt(value, *, default_now=False):
    """Normalize a timestamp without inventing freshness."""
    if value is None:
        return datetime.now(timezone.utc).isoformat() if default_now else None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _canonical_source_key(bridge_source_key, record):
    """Preserve authoritative upstream provenance from aggregate adapters.

    Aggregate SEWS collectors often return an AgentSignal with its own
    source_key (for example EIA or OFAC). Prefer a recognized canonical source
    over the aggregate adapter label. Unknown/internal sources remain attached
    to the bridge source so we never invent attribution.
    """
    upstream = _first(record, "source_key", "source", "provider", "publisher")
    if not upstream:
        return bridge_source_key
    normalized = " ".join(str(upstream).strip().lower().split())
    if normalized in SOURCE_ALIASES:
        return SOURCE_ALIASES[normalized]
    for alias, canonical in SOURCE_ALIASES.items():
        if alias in normalized:
            return canonical
    return bridge_source_key


def normalize_existing_record(*, source_key, raw_record, problem_key, country_iso3, region_key, query):
    record = raw_record.model_dump(mode="json") if hasattr(raw_record, "model_dump") else (
        raw_record if isinstance(raw_record, dict) else {"value": raw_record}
    )
    canonical_source_key = _canonical_source_key(source_key, record)
    title = str(_first(record, "title", "name", "headline", "series_name", "indicator_name") or f"{canonical_source_key} intelligence record")
    text = str(_first(record, "raw_text", "summary", "description", "content", "snippet", "value") or title)
    url = _first(record, "canonical_url", "url", "link", "source_url")
    external_id = _first(record, "source_external_id", "id", "guid", "globaleventid", "series_id", "signal_id")
    identity = json.dumps({"source": canonical_source_key, "id": external_id, "url": url, "title": title, "problem": problem_key}, sort_keys=True, default=str)
    digest = hashlib.sha256(identity.encode()).hexdigest()
    timestamp_present = _first(
        record,
        "published_at",
        "published",
        "date",
        "seendate",
        "updated_at",
        "observed_at",
        "timestamp",
    )
    return {
        "signal_key": f"BRIDGE-{canonical_source_key}-{digest[:32]}",
        "source_key": canonical_source_key,
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
            "canonical_source_key": canonical_source_key,
            "upstream_source": _first(record, "source_key", "source", "provider", "publisher"),
            "existing_platform_record": record,
            "timestamp_quality": "observed" if timestamp_present else "unknown",
        },
    }
