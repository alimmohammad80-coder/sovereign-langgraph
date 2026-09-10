from app.routes.sews_causal_simulation import router as sews_causal_simulation_router
from app.routes.supply_chain_geo import router as supply_chain_geo_router
from app.routes.supply_chain_ingestion import router as supply_chain_ingestion_router
from app.routes import global_risk
from routers.context_memory import router as context_memory_router
from routers.scenario_analysis import router as scenario_analysis_router
from routers.country_intelligence import router as country_intelligence_router
from app.routes.ingestion import router as ingestion_router
from app.routes.alert_orchestrator import router as alert_orchestrator_router
from fastapi import FastAPI
import os
from app.security import PlatformSecurityMiddleware
from app.routers import signals
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routes.sews_evidence import router as sews_evidence_router
from app.routes.sews_warning_scoring import router as sews_warning_scoring_router
from app.routes.sews_warning_ledger import router as sews_warning_ledger_router
from app.routes.sews_ai_review import router as sews_ai_review_router
from app.routes.strategic_intelligence_products import router as strategic_intelligence_products_router
from app.routes.sews_bridge import router as sews_bridge_router
from app.routes.sews_runtime_initialization import router as sews_runtime_initialization_router
from app.routes.sews_operational_intelligence import router as sews_operational_intelligence_router
from app.routes.sews_executive_brief import router as sews_executive_brief_router
from app.routes.sews_operations import router as sews_operations_router
from app.cyber_information import router as cyber_information_router
load_dotenv()

from app.routes.sews_warning_baselines import router as sews_warning_baselines_router
from app.routes.intelligence_retrieval import router as intelligence_retrieval_router
from routers.strategic_knowledge_graph import router as strategic_knowledge_graph_router
from app.routes import supply_chain
from app.routers.conflict_forecasting import router as conflict_forecasting_router
from app.routes.conflict_intelligence import router as conflict_intelligence_router
from app.routes.intelligence_pipeline import router as intelligence_pipeline_router
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
from routes.financial_corporate_intelligence import router as financial_corporate_intelligence_router
from routes.financial_corporate_universe import router as financial_corporate_universe_router
from routes.financial_corporate_market_credit import router as financial_corporate_market_credit_router
from routes.financial_corporate_distress_portfolio import router as financial_corporate_distress_portfolio_router
from routes.financial_corporate_cross_module import router as financial_corporate_cross_module_router
from routes.financial_corporate_integrated import router as financial_corporate_integrated_router
from routes.financial_corporate_reports import router as financial_corporate_reports_router
from routes.financial_command import router as financial_command_router
from app.routes.early_warning import router as early_warning_router
from app.routes.early_warning_agents import router as early_warning_agents_router
from app.routes.simulation_lab import router as simulation_lab_router
from app.routes.fusion import router as fusion_router
from app.routes import scenario
from app.routes import simulation
from app.routes.strategic_agents import router as strategic_agents_router
from app.routes.strategic_reports import router as strategic_reports_router
from app.routes.siam import router as siam_router
from app.routes.sews import router as sews_router

from routers.personal_agent import router as personal_agent_router
from routers.module_access import router as module_access_router
from routers.usage import router as usage_router

app = FastAPI(
    title="Sovereign Intelligence API",
    version="1.0.0",
    description="Sovereign Intelligence backend for geopolitical, security, energy, dashboard, signals, ingestion, supply chain, and financial/corporate risk intelligence."
)

DEFAULT_ALLOWED_ORIGINS = {
    "https://sovereignintel.ai",
    "https://www.sovereignintel.ai",
    "https://sovereignintelligence.app",
    "https://www.sovereignintelligence.app",
    "http://localhost:8080",
    "http://localhost:5173",
}
configured_origins = {
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
}
allowed_origins = sorted(DEFAULT_ALLOWED_ORIGINS | configured_origins)

app.add_middleware(PlatformSecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https://([a-z0-9-]+\.)*(lovable\.app|lovableproject\.com|lovableproject-dev\.com|gpt-eng\.com|gptengineer\.run)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core platform routers
app.include_router(sews_causal_simulation_router)
app.include_router(sews_evidence_router)
app.include_router(sews_warning_baselines_router)
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
app.include_router(conflict_intelligence_router)
app.include_router(strategic_knowledge_graph_router)
app.include_router(supply_chain_geo_router)
app.include_router(supply_chain_ingestion_router)
app.include_router(cyber_information_router)

# Supply Chain / legacy financial routers retained for compatibility.
app.include_router(supply_chain_router)
app.include_router(financial_risk_router)
app.include_router(corporate_exposure_router)

# Financial & Corporate intelligence internals.
app.include_router(financial_corporate_intelligence_router)
app.include_router(financial_corporate_universe_router)
app.include_router(financial_corporate_market_credit_router)
app.include_router(financial_corporate_distress_portfolio_router)
app.include_router(financial_corporate_cross_module_router)
app.include_router(financial_corporate_integrated_router)
app.include_router(financial_corporate_reports_router)

# Canonical Financial Risk Command v2 public contract.
app.include_router(financial_command_router)

app.include_router(early_warning_router)
app.include_router(early_warning_agents_router)
app.include_router(fusion_router)

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Sovereign Intelligence API running",
        "version": "financial-risk-command-v2",
        "modules": [
            "ingest",
            "signals",
            "dashboard",
            "supply_chain_risk",
            "financial_risk_command",
        ],
    }

@app.get("/health")
def health():
    return {
        "health": "healthy",
        "status": "ok",
        "service": "sovereign-intelligence-api",
    }

@app.get("/routes")
def list_routes():
    return [
        {"path": route.path, "methods": sorted(list(route.methods or []))}
        for route in app.routes
    ]

app.include_router(signals.router)
app.include_router(intelligence_retrieval_router)
app.include_router(scenario.router)
app.include_router(simulation.router)
app.include_router(alert_orchestrator_router)
app.include_router(ingestion_router)
app.include_router(country_intelligence_router)
app.include_router(scenario_analysis_router)
app.include_router(context_memory_router)

app.include_router(personal_agent_router, prefix="/api/agent", tags=["Personal Agent"])
app.include_router(module_access_router, prefix="/api", tags=["Module Access"])
app.include_router(usage_router, prefix="/api/usage", tags=["Usage"])

app.include_router(global_risk.router)
app.include_router(strategic_agents_router)
app.include_router(strategic_reports_router)
app.include_router(siam_router)
app.include_router(sews_router)
app.include_router(sews_warning_scoring_router)
app.include_router(sews_warning_ledger_router)
app.include_router(sews_ai_review_router)
app.include_router(strategic_intelligence_products_router)
app.include_router(sews_bridge_router)
app.include_router(sews_runtime_initialization_router)
app.include_router(sews_operational_intelligence_router)
app.include_router(sews_executive_brief_router)
app.include_router(sews_operations_router)

REQUIRED_ROUTE_PREFIXES = [
    "/api/country-intelligence",
    "/api/conflict",
    "/api/conflict-intelligence",
    "/api/cyber-information",
    "/api/sews",
    "/api/supply-chain",
    "/api/financial",
    "/api/scenario",
    "/api/simulation",
]

def validate_canonical_routes() -> set[str]:
    app.openapi_schema = None
    paths = set(app.openapi().get("paths", {}).keys())
    missing_route_prefixes = [
        prefix
        for prefix in REQUIRED_ROUTE_PREFIXES
        if not any(path.startswith(prefix) for path in paths)
    ]
    if missing_route_prefixes:
        raise RuntimeError(
            "Canonical Sovereign Intelligence API is missing critical route families: "
            + ", ".join(missing_route_prefixes)
        )
    return paths

@app.get("/api/platform/health", tags=["Platform"])
def platform_health():
    checks = {
        "country_intelligence": "/api/country-intelligence",
        "conflict_forecasting": "/api/conflict",
        "conflict_intelligence": "/api/conflict-intelligence",
        "cyber_information": "/api/cyber-information",
        "strategic_early_warning": "/api/sews",
        "supply_chain": "/api/supply-chain",
        "financial_risk_command": "/api/financial",
        "scenario": "/api/scenario",
        "simulation": "/api/simulation",
        "global_risk": "/api/global",
        "personal_agent": "/api/agent",
    }
    app.openapi_schema = None
    paths = set(app.openapi().get("paths", {}).keys())
    modules = {
        name: {"registered": any(path.startswith(prefix) for path in paths), "prefix": prefix}
        for name, prefix in checks.items()
    }
    healthy = all(module["registered"] for module in modules.values())
    return {
        "status": "healthy" if healthy else "degraded",
        "service": "Sovereign Intelligence API",
        "canonical_app": "app.main:app",
        "route_count": len(paths),
        "modules": modules,
    }

from app.services.strategic_agents.scheduled_runner import strategic_agent_scheduled_runner

@app.on_event("startup")
async def start_strategic_agent_scheduler() -> None:
    paths = validate_canonical_routes()
    print("[Platform] Canonical route validation passed:", len(paths), "OpenAPI paths")
    await strategic_agent_scheduled_runner.start()

@app.on_event("shutdown")
async def stop_strategic_agent_scheduler() -> None:
    await strategic_agent_scheduled_runner.stop()
