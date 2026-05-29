from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.financial_risk import router as financial_risk_router
from routes.corporate_exposure import router as corporate_exposure_router
from routers.supply_chain import router as supply_chain_router

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

@app.get("/")
def root():
    return {"status": "ok", "service": "Sovereign Intelligence API"}

app.include_router(supply_chain_router)

@app.get("/routes")
def list_routes():
    return [
        {
            "path": route.path,
            "methods": list(route.methods or [])
        }
        for route in app.routes
    ]
