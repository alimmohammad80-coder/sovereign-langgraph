from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.conflict_intelligence import router


def test_health():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/api/conflict-intelligence/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["deterministic"] is True
    assert payload["data"]["ai_scoring_enabled"] is False
