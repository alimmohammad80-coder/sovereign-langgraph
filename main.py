from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.financial_risk import router as financial_risk_router
from routes.corporate_exposure import router as corporate_exposure_router
from routes.financial_corporate_intelligence import router as financial_corporate_intelligence_router
from routes.financial_corporate_universe import router as financial_corporate_universe_router
from routes.financial_corporate_market_credit import router as financial_corporate_market_credit_router
from routes.financial_corporate_distress_portfolio import router as financial_corporate_distress_portfolio_router
from routes.financial_corporate_cross_module import router as financial_corporate_cross_module_router
from routers.supply_chain import router as supply_chain_router
from routers.optimization import router as optimization_router


from routers.personal_agent import router as personal_agent_router
from routers.module_access import router as module_access_router
from routers.usage import router as usage_router

app = FastAPI(
    title="Sovereign Intelligence API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(financial_risk_router)
app.include_router(corporate_exposure_router)
app.include_router(financial_corporate_intelligence_router)
app.include_router(financial_corporate_universe_router)
app.include_router(financial_corporate_market_credit_router)
app.include_router(financial_corporate_distress_portfolio_router)
app.include_router(financial_corporate_cross_module_router)

@app.get("/")
def root():
    return {"status": "ok", "service": "Sovereign Intelligence API"}

app.include_router(supply_chain_router)
app.include_router(optimization_router)


@app.get("/routes")
def list_routes():
    return [
        {
            "path": route.path,
            "methods": list(route.methods or [])
        }
        for route in app.routes
    ]


app.include_router(personal_agent_router, prefix="/api/agent", tags=["Personal Agent"])
app.include_router(module_access_router, prefix="/api", tags=["Module Access"])
app.include_router(usage_router, prefix="/api/usage", tags=["Usage"])

