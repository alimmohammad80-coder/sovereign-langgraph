from app.sews_bridge.discovery import import_callable
from app.sews_bridge.normalization import normalize_existing_record

def test_google_news_existing_callable_resolves():
    assert callable(import_callable("app.intelligence.sources.google_news:fetch_google_news"))

def test_existing_record_normalization():
    record = normalize_existing_record(
        source_key="GOOGLE_NEWS_RSS",
        raw_record={"title": "Shipping disruption near Hormuz", "summary": "Traffic disrupted.", "url": "https://example.com/1"},
        problem_key="WP-HORMUZ-CLOSURE",
        country_iso3="IRN",
        region_key="MIDDLE_EAST",
        query="Hormuz shipping disruption",
    )
    assert record["metadata"]["warning_problem_key"] == "WP-HORMUZ-CLOSURE"
    assert record["country_iso3"] == "IRN"
