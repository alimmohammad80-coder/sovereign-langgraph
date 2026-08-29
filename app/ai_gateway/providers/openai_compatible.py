from __future__ import annotations
import json
import os
import time
from typing import Any
from openai import OpenAI
from app.ai_gateway.providers.base import BaseAIProvider
from app.ai_gateway.schemas import AIGatewayRequest, AIGatewayResponse, AIResponseFormat

class OpenAICompatibleProvider(BaseAIProvider):
    def __init__(self, *, provider_key: str, api_key_env: str, base_url_env: str,
                 default_base_url: str, model_env: str, default_model: str) -> None:
        self.provider_key = provider_key.upper()
        self.api_key_env = api_key_env
        self.base_url_env = base_url_env
        self.default_base_url = default_base_url
        self.model_env = model_env
        self.default_model = default_model

    def is_configured(self) -> bool:
        return bool(os.getenv(self.api_key_env))

    def _client(self) -> OpenAI:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"{self.provider_key} missing {self.api_key_env}")
        return OpenAI(
            api_key=api_key,
            base_url=os.getenv(self.base_url_env, self.default_base_url),
            timeout=120.0,
            max_retries=1,
        )

    def generate(self, request: AIGatewayRequest) -> AIGatewayResponse:
        client = self._client()
        model = request.preferred_model or os.getenv(self.model_env) or self.default_model
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": request.temperature,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.response_format == AIResponseFormat.JSON:
            kwargs["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        response = client.chat.completions.create(**kwargs)
        latency_ms = int((time.perf_counter() - started) * 1000)
        content = response.choices[0].message.content or ""
        parsed_json = json.loads(content) if request.response_format == AIResponseFormat.JSON else None

        usage = {}
        if getattr(response, "usage", None):
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                "completion_tokens": getattr(response.usage, "completion_tokens", None),
                "total_tokens": getattr(response.usage, "total_tokens", None),
            }

        return AIGatewayResponse(
            provider=self.provider_key,
            model=model,
            task_type=request.task_type,
            content=content,
            parsed_json=parsed_json,
            latency_ms=latency_ms,
            usage=usage,
            metadata=request.metadata,
        )
