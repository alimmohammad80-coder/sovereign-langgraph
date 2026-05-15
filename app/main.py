from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.fusion_signals import router as fusion_signals_router
from app.routes.risk_signals import router as risk_signals_router
from app.routes.google_news import router as google_news_router
from app.routes.ingestion_admin import router as ingestion_admin_router
from app.routes.news_cache import router as news_cache_router
from app.routes.gdelt import router as gdelt_router
from app.api.ingest import router as ingest_router
from app.api.signals import router as signals_router
from app.api.dashboard import router as dashboard_router
from routers.supply_chain import router as supply_chain_router
from routes.financial_risk import router as financial_risk_router
from routes.corporate_exposure import router as corporate_exposure_router
from app.routes.early_warning import router as early_warning_router
from app.routes.early_warning_agents import router as early_warning_agents_router
from app.routes.simulation_lab import router as simulation_lab_router

from app.routes.fusion import router as fusion_router

app = FastAPI(
    title="Sovereign Intelligence API",
    version="1.0.0",
    description="Sovereign Intelligence backend for geopolitical, security, energy, dashboard, signals, ingestion, and supply chain risk intelligence."
)

# CORS configuration
# Keep permissive during development. Later, replace '*' with your Lovable/production frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core platform routers
app.include_router(gdelt_router)
app.include_router(ingest_router)
app.include_router(signals_router)
app.include_router(dashboard_router)
app.include_router(news_cache_router)
app.include_router(ingestion_admin_router)
app.include_router(google_news_router)
app.include_router(risk_signals_router)
app.include_router(fusion_signals_router)
app.include_router(simulation_lab_router)

# Supply Chain Risk Engine router
app.include_router(supply_chain_router)
app.include_router(financial_risk_router)
app.include_router(corporate_exposure_router)
app.include_router(early_warning_router)
app.include_router(early_warning_agents_router)
app.include_router(fusion_router)

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Sovereign Intelligence API running",
        "version": "supply-chain-routes-enabled",
        "modules": [
            "ingest",
            "signals",
            "dashboard",
            "supply_chain_risk"
        ]
    }


@app.get("/health")
def health():
    return {
        "health": "healthy",
        "status": "ok",
        "service": "sovereign-intelligence-api"
    }


@app.get("/routes")
def list_routes():
    return [
        {
            "path": route.path,
            "methods": sorted(list(route.methods or []))
        }
        for route in app.routes
    ]
