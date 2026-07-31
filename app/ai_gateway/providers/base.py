from __future__ import annotations
from abc import ABC, abstractmethod
from app.ai_gateway.schemas import AIGatewayRequest, AIGatewayResponse

class BaseAIProvider(ABC):
    provider_key: str

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: AIGatewayRequest) -> AIGatewayResponse:
        raise NotImplementedError
