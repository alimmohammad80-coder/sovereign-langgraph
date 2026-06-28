
from app.routes.supply_chain_geo import router as supply_chain_geo_router
from app.routes import global_risk
from routers.context_memory import router as context_memory_router
from routers.scenario_analysis import router as scenario_analysis_router
from routers.country_intelligence import router as country_intelligence_router
from app.routes.ingestion import router as ingestion_router
from app.routes.alert_orchestrator import router as alert_orchestrator_router
from app.routes import global_risk
from fastapi import FastAPI
from app.routers import signals
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from app.routes.intelligence_retrieval import router as intelligence_retrieval_router
from app.routes import global_risk
from routers.strategic_knowledge_graph import router as strategic_knowledge_graph_router
from app.routes import supply_chain
from app.routes import global_risk
from app.routers.conflict_forecasting import router as conflict_forecasting_router
from app.routes.intelligence_pipeline import router as intelligence_pipeline_router
from app.routes import global_risk
from app.routes.fusion_signals import router as fusion_signals_router
from app.routes import global_risk
from app.routes.risk_signals import router as risk_signals_router
from app.routes import global_risk
from app.routes.google_news import router as google_news_router
from app.routes import global_risk
from app.routes.ingestion_admin import router as ingestion_admin_router
from app.routes import global_risk
from app.routes.news_cache import router as news_cache_router
from app.routes import global_risk
from app.routes.gdelt import router as gdelt_router
from app.routes import global_risk
from app.api.ingest import router as ingest_router
from app.api.signals import router as signals_router
from app.api.dashboard import router as dashboard_router
from routers.supply_chain import router as supply_chain_router
from routes.financial_risk import router as financial_risk_router
from routes.corporate_exposure import router as corporate_exposure_router
from app.routes.early_warning import router as early_warning_router
from app.routes import global_risk
from app.routes.early_warning_agents import router as early_warning_agents_router
from app.routes import global_risk
from app.routes.simulation_lab import router as simulation_lab_router
from app.routes import global_risk

from app.routes.fusion import router as fusion_router
from app.routes import global_risk
from app.routes import scenario
from app.routes import global_risk
from app.routes import simulation_lab
from app.routes import global_risk
from app.routes import simulation
from app.routes import global_risk


from routers.personal_agent import router as personal_agent_router
from routers.module_access import router as module_access_router
from routers.usage import router as usage_router

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
app.include_router(intelligence_pipeline_router)
app.include_router(conflict_forecasting_router)
app.include_router(strategic_knowledge_graph_router)
app.include_router(supply_chain_geo_router)

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


app.include_router(signals.router)
app.include_router(intelligence_retrieval_router)

# Scenario Simulation Lab
app.include_router(scenario.router)

# Refined legacy Simulation Lab route
app.include_router(simulation_lab.router)

# Simulation Lab legacy alias route
app.include_router(simulation.router)

# Alert Orchestrator
app.include_router(alert_orchestrator_router)

# Live Signal Ingestion
app.include_router(ingestion_router)

# Country Intelligence
app.include_router(country_intelligence_router)

# Scenario Analysis
app.include_router(scenario_analysis_router)

# Context Memory
app.include_router(context_memory_router)


app.include_router(personal_agent_router, prefix="/api/agent", tags=["Personal Agent"])
app.include_router(module_access_router, prefix="/api", tags=["Module Access"])
app.include_router(usage_router, prefix="/api/usage", tags=["Usage"])


app.include_router(global_risk.router)
