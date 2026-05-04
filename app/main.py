from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ingest import router as ingest_router
from app.api.signals import router as signals_router
from app.api.dashboard import router as dashboard_router
from routers.supply_chain import router as supply_chain_router


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
app.include_router(ingest_router)
app.include_router(signals_router)
app.include_router(dashboard_router)

# Supply Chain Risk Engine router
app.include_router(supply_chain_router)


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
