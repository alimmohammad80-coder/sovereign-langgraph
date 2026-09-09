import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

import app.security as security
from app.routes.supply_chain_ingestion import _authorize


def _client(monkeypatch, modules=(), *, admin=False, internal=False):
    monkeypatch.setattr(
        security,
        "verify_supabase_token",
        lambda token: {"id": "token-user", "app_metadata": {"tenant_id": "token-tenant"}}
        if token == "valid"
        else (_ for _ in ()).throw(ValueError("invalid")),
    )
    monkeypatch.setattr(
        security,
        "build_user_context",
        lambda user_id: {
            "user": {"id": user_id},
            "access": {
                "modules": list(modules),
                "is_admin": admin,
                "is_internal": internal,
            },
        },
    )
    test_app = FastAPI()
    test_app.add_middleware(security.PlatformSecurityMiddleware)

    @test_app.get("/")
    @test_app.get("/health")
    @test_app.get("/api/platform/health")
    def public():
        return {"ok": True}

    @test_app.get("/api/financial-corporate/integrated/status")
    @test_app.get("/api/financial-corporate/reports/status")
    @test_app.get("/api/country-intelligence/status")
    def protected(request: Request):
        return {"user_id": request.state.user_id, "tenant_id": request.state.tenant_id}

    @test_app.get("/api/unclassified/new-feature")
    def unclassified():
        return {"unsafe": True}

    return TestClient(test_app)


@pytest.mark.parametrize("path", ["/", "/health", "/api/platform/health"])
def test_only_health_endpoints_are_public(monkeypatch, path):
    assert _client(monkeypatch).get(path).status_code == 200


def test_missing_and_invalid_tokens_return_401(monkeypatch):
    client = _client(monkeypatch, ["country_intelligence"])
    assert client.get("/api/country-intelligence/status").status_code == 401
    assert client.get("/api/country-intelligence/status", headers={"Authorization": "Basic valid"}).status_code == 401
    assert client.get("/api/country-intelligence/status", headers={"Authorization": "Bearer bad"}).status_code == 401


def test_entitlement_and_token_identity(monkeypatch):
    denied = _client(monkeypatch).get(
        "/api/country-intelligence/status", headers={"Authorization": "Bearer valid"}
    )
    assert denied.status_code == 403

    response = _client(monkeypatch, ["country_intelligence"]).get(
        "/api/country-intelligence/status?tenant_id=caller-tenant",
        headers={"Authorization": "Bearer valid", "X-Tenant-ID": "caller-tenant"},
    )
    assert response.status_code == 200
    assert response.json() == {"user_id": "token-user", "tenant_id": "token-tenant"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/financial-corporate/integrated/status",
        "/api/financial-corporate/reports/status",
    ],
)
def test_financial_integrated_and_report_routes_are_protected(monkeypatch, path):
    assert _client(monkeypatch).get(path).status_code == 401
    assert _client(monkeypatch).get(path, headers={"Authorization": "Bearer valid"}).status_code == 403
    assert _client(monkeypatch, ["financial_risk"]).get(
        path, headers={"Authorization": "Bearer valid"}
    ).status_code == 200


def test_unclassified_api_routes_default_deny_but_admin_bypasses(monkeypatch):
    path = "/api/unclassified/new-feature"
    assert _client(monkeypatch, list(security.entitlement_modules())).get(
        path, headers={"Authorization": "Bearer valid"}
    ).status_code == 403
    assert _client(monkeypatch, admin=True).get(
        path, headers={"Authorization": "Bearer valid"}
    ).status_code == 200


def test_financial_report_routes_registered():
    from app.main import app

    paths = set(app.openapi()["paths"])
    assert any(path.startswith("/api/financial-corporate/reports/") for path in paths)


def test_canonical_route_inventory_is_classified():
    from app.main import app

    paths = set(app.openapi()["paths"])
    expected_default_denials = {"/api/admin/run-ingestion"}
    default_denials = {
        path
        for path in paths
        if path not in security.PUBLIC_PATHS
        and security.required_module(path) == "__default_deny__"
    }
    assert default_denials == expected_default_denials


def test_supply_chain_ingestion_token_fails_closed(monkeypatch):
    monkeypatch.delenv("SUPPLY_CHAIN_INGESTION_TOKEN", raising=False)
    with pytest.raises(Exception) as missing:
        _authorize(None)
    assert missing.value.status_code == 403

    monkeypatch.setenv("SUPPLY_CHAIN_INGESTION_TOKEN", "secret")
    with pytest.raises(Exception) as wrong:
        _authorize("wrong")
    assert wrong.value.status_code == 403
    _authorize("secret")
