from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class SourceDefinition:
    source_key: str
    candidates: tuple[str, ...]
    kind: str

SOURCE_DEFINITIONS = (
    SourceDefinition("SEWS_ECONOMIC", (
        "app.services.sews_authoritative_collection_adapter:"
        "fetch_sews_economic_intelligence",
    ), "AUTHORITATIVE"),
    SourceDefinition("SEWS_ENERGY", (
        "app.services.sews_authoritative_collection_adapter:"
        "fetch_sews_energy_intelligence",
    ), "AUTHORITATIVE"),
    SourceDefinition("SEWS_CONFLICT", (
        "app.services.sews_authoritative_collection_adapter:"
        "fetch_sews_conflict_intelligence",
    ), "AUTHORITATIVE"),
    SourceDefinition("SEWS_POLITICAL", (
        "app.services.sews_authoritative_collection_adapter:"
        "fetch_sews_political_intelligence",
    ), "AUTHORITATIVE"),
    SourceDefinition("SEWS_TRADE_SANCTIONS", (
        "app.services.sews_authoritative_collection_adapter:"
        "fetch_sews_trade_sanctions_intelligence",
    ), "AUTHORITATIVE"),
    SourceDefinition("GOOGLE_NEWS_RSS", (
        "app.intelligence.sources.google_news:fetch_google_news",
        "app.services.google_news_service:fetch_google_news",
    ), "NEWS"),
    SourceDefinition("GDELT", (
        "app.services.gdelt_service:fetch_gdelt_news",
        "app.services.gdelt_service:search_gdelt",
        "app.intelligence.sources.gdelt:fetch_gdelt",
    ), "NEWS"),
    SourceDefinition("NEWSAPI", (
        "app.services.sovereign_news_ingestion:fetch_newsapi",
        "app.services.news_service:fetch_newsapi",
        "app.intelligence.sources.newsapi:fetch_news",
    ), "NEWS"),
    SourceDefinition("WORLD_BANK", (
        "app.services.worldbank_service:_fetch_indicator",
        "app.services.world_bank_service:fetch_indicator",
        "app.services.macro_data_service:get_world_bank_data",
    ), "TIME_SERIES"),
    SourceDefinition("IMF", (
        "app.services.imf_service:fetch_imf_indicator",
        "app.services.imf_service:fetch_indicator",
        "app.services.macro_data_service:get_imf_data",
    ), "TIME_SERIES"),
    SourceDefinition("FRED", (
        "app.services.fred_service:fetch_fred_series",
        "app.services.fred_service:fetch_series",
        "app.services.macro_data_service:get_fred_data",
    ), "TIME_SERIES"),
    SourceDefinition("EIA", (
        "app.services.eia_service:fetch_eia_series",
        "app.services.eia_service:fetch_series",
        "app.services.energy_data_service:get_eia_data",
    ), "TIME_SERIES"),
    SourceDefinition("RELIEFWEB", (
        "app.services.reliefweb_service:fetch_reports",
        "app.intelligence.sources.reliefweb:fetch_reports",
    ), "NEWS"),
    SourceDefinition("OFAC", (
        "app.services.ofac_service:fetch_updates",
        "app.services.sanctions_service:get_ofac_updates",
    ), "EVENT"),
)
