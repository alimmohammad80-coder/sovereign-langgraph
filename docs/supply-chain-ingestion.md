# Supply Chain external evidence ingestion

This ingestion layer normalizes external evidence for the Global Supply Chain
Intelligence module. It stores every observation in `sc_external_evidence`.
Entity-matched event records are also promoted to
`sc_live_disruption_events`, which is consumed by the live report generator.

## Sources

| Key | Source | Configuration |
| --- | --- | --- |
| `GDELT` | GDELT DOC 2.0 | Ready without credentials |
| `IMF_PORTWATCH` | IMF PortWatch export/API | `PORTWATCH_API_URL` or request `portwatch_url` |
| `GDACS` | GDACS RSS | Ready without credentials |
| `USGS` | USGS real-time earthquake GeoJSON | Ready without credentials |
| `UN_COMTRADE` | UN Comtrade | Request `reporter_code`; optional `UN_COMTRADE_API_KEY` |
| `EIA` | U.S. EIA v2 | `EIA_API_KEY` and request `eia_route` |
| `OFAC` | OFAC SDN XML | Ready without credentials |
| `SEC_EDGAR` | SEC submissions API | `SEC_USER_AGENT`, request `company_cik` |
| `GLEIF` | GLEIF LEI API | Request `company_name` |
| `OFFICIAL_FEEDS` | Company and port RSS/Atom | Request `official_feed_urls` |

Set `SUPPLY_CHAIN_INGESTION_TOKEN` in production. When configured, POST
requests must send it in the `X-Ingestion-Token` header.

## Endpoints

List collector readiness:

```text
GET /api/supply-chain/ingestion/sources
```

Run a public event collector:

```bash
curl -X POST "$BASE/api/supply-chain/ingestion/run/GDACS" \
  -H "X-Ingestion-Token: $SUPPLY_CHAIN_INGESTION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_records": 100}'
```

Run company-specific sources:

```bash
curl -X POST "$BASE/api/supply-chain/ingestion/run" \
  -H "X-Ingestion-Token: $SUPPLY_CHAIN_INGESTION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["SEC_EDGAR", "GLEIF"],
    "contexts": {
      "SEC_EDGAR": {
        "company_name": "TSMC",
        "company_cik": "1046179",
        "max_records": 20
      },
      "GLEIF": {
        "company_name": "Taiwan Semiconductor Manufacturing Company"
      }
    }
  }'
```

Run trade and energy collection with explicit dataset parameters:

```json
{
  "sources": ["UN_COMTRADE", "EIA"],
  "contexts": {
    "UN_COMTRADE": {
      "reporter_code": "158",
      "country_iso3": "TWN",
      "commodity_code": "8542",
      "flow_code": "X",
      "period": "2025"
    },
    "EIA": {
      "eia_route": "international/data",
      "commodity": "Crude Oil",
      "frequency": "monthly",
      "data_fields": ["value"],
      "facets": {}
    }
  }
}
```

## Operational behavior

Collectors run independently and fail soft. One unavailable provider does not
block other collectors. Evidence is upserted by `(source, source_record_id)`
in batches of 100. Events are promoted only after matching a known company,
port, chokepoint, commodity, or corridor. USGS events may also match the
nearest known port within 250 km.

Apply `supabase/migrations/20260904_002_supply_chain_external_evidence.sql`
before enabling the endpoints.
