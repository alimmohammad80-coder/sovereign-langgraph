from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.include_router(supply_chain_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Sovereign Intelligence API running"
    }
