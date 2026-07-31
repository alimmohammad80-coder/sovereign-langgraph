from __future__ import annotations
from typing import Iterable
from app.ai_gateway.providers.base import BaseAIProvider
from app.ai_gateway.routing import DEFAULT_ROUTES
from app.ai_gateway.schemas import AIGatewayRequest, AIGatewayResponse

class AIGatewayError(RuntimeError):
    pass

class AIGateway:
    def __init__(self, providers: Iterable[BaseAIProvider]) -> None:
        self._providers = {p.provider_key.upper(): p for p in providers}

    def available_providers(self) -> list[str]:
        return sorted(k for k, p in self._providers.items() if p.is_configured())

    def generate(self, request: AIGatewayRequest) -> AIGatewayResponse:
        candidates = (
            [request.preferred_provider.upper()]
            if request.preferred_provider
            else DEFAULT_ROUTES.get(request.task_type, type("R", (), {"providers": []})()).providers
        )
        errors: list[str] = []
        for provider_key in candidates:
            provider = self._providers.get(provider_key)
            if provider is None:
                errors.append(f"{provider_key}: not registered")
                continue
            if not provider.is_configured():
                errors.append(f"{provider_key}: not configured")
                continue
            try:
                return provider.generate(request)
            except Exception as exc:
                errors.append(f"{provider_key}: {type(exc).__name__}: {exc}")
        raise AIGatewayError("No provider completed the request. " + " | ".join(errors))
