# SEWS Existing Sources Bridge

This bridge reuses the platform's existing source services and existing Render
environment variables. It does not rebuild external API clients.

## Endpoints

GET /api/sews/integration/status
POST /api/sews/integration/run

The status endpoint reports which exact existing callables were found. Google
News RSS should resolve from:

app.intelligence.sources.google_news:fetch_google_news

For any unavailable source, add its actual existing callable import path to:

app/sews_bridge/source_registry.py

## Register

from app.routes.sews_bridge import router as sews_bridge_router
app.include_router(sews_bridge_router)

## Test

PYTHONPATH=. pytest tests/test_sews_bridge.py -v
