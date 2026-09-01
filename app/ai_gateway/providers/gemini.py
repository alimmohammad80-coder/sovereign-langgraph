from __future__ import annotations

import json
import os
import time
from typing import Any

from google import genai
from google.genai import types

from app.ai_gateway.providers.base import BaseAIProvider
from app.ai_gateway.schemas import (
    AIGatewayRequest,
    AIGatewayResponse,
    AIResponseFormat,
)


class GeminiProvider(BaseAIProvider):

    provider_key = "GEMINI"

    def __init__(
        self,
        *,
        api_key_env: str = "GEMINI_API_KEY",
        model_env: str = "GEMINI_MODEL",
        default_model: str = "gemini-3.1-pro-preview",
    ) -> None:
        self.api_key_env = api_key_env
        self.model_env = model_env
        self.default_model = default_model

    def is_configured(self) -> bool:
        return bool(
            os.getenv(self.api_key_env)
            or os.getenv("GOOGLE_API_KEY")
        )

    def _client(self) -> genai.Client:
        api_key = (
            os.getenv(self.api_key_env)
            or os.getenv("GOOGLE_API_KEY")
        )

        if not api_key:
            raise RuntimeError(
                "GEMINI missing GEMINI_API_KEY/GOOGLE_API_KEY"
            )

        return genai.Client(
            api_key=api_key
        )

    def generate(
        self,
        request: AIGatewayRequest,
    ) -> AIGatewayResponse:

        client = self._client()

        model = (
            request.preferred_model
            or os.getenv(self.model_env)
            or os.getenv("GEMINI_ANALYST_MODEL")
            or self.default_model
        )

        config_kwargs: dict[str, Any] = {
            "system_instruction":
                request.system_prompt,

            "temperature":
                request.temperature,
        }

        if request.max_tokens is not None:
            config_kwargs[
                "max_output_tokens"
            ] = request.max_tokens

        if (
            request.response_format
            == AIResponseFormat.JSON
        ):
            config_kwargs[
                "response_mime_type"
            ] = "application/json"

        started = time.perf_counter()

        response = (
            client.models.generate_content(
                model=model,
                contents=request.user_prompt,
                config=types.GenerateContentConfig(
                    **config_kwargs
                ),
            )
        )

        content = (
            response.text
            or ""
        )

        parsed_json = None
        json_retry_used = False

        if (
            request.response_format
            == AIResponseFormat.JSON
        ):
            try:
                parsed_json = json.loads(
                    content
                )

            except json.JSONDecodeError:
                #
                # A structured Gemini response can occasionally be
                # truncated even when application/json is requested.
                # Never heuristically repair analytical output.
                # Retry generation once and require a complete JSON
                # document so gateway validation remains authoritative.
                #
                json_retry_used = True

                retry_config = dict(
                    config_kwargs
                )

                original_max_tokens = (
                    request.max_tokens
                    or 12000
                )

                retry_config[
                    "max_output_tokens"
                ] = min(
                    max(
                        original_max_tokens,
                        20000,
                    ),
                    30000,
                )

                retry_prompt = (
                    request.user_prompt
                    + "\n\n"
                    + (
                        "IMPORTANT OUTPUT REQUIREMENT: "
                        "Return one complete valid JSON object only. "
                        "Do not use markdown fences. "
                        "Do not truncate the response. "
                        "Keep narrative fields concise enough for the "
                        "entire JSON document to finish within the "
                        "available output budget."
                    )
                )

                response = (
                    client.models.generate_content(
                        model=model,
                        contents=retry_prompt,
                        config=types.GenerateContentConfig(
                            **retry_config
                        ),
                    )
                )

                content = (
                    response.text
                    or ""
                )

                parsed_json = json.loads(
                    content
                )

        latency_ms = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        usage: dict[str, Any] = {}

        usage_metadata = getattr(
            response,
            "usage_metadata",
            None,
        )

        if usage_metadata is not None:
            usage = {
                "prompt_tokens":
                    getattr(
                        usage_metadata,
                        "prompt_token_count",
                        None,
                    ),

                "completion_tokens":
                    getattr(
                        usage_metadata,
                        "candidates_token_count",
                        None,
                    ),

                "total_tokens":
                    getattr(
                        usage_metadata,
                        "total_token_count",
                        None,
                    ),
            }

        return AIGatewayResponse(
            provider=self.provider_key,
            model=model,
            task_type=request.task_type,
            content=content,
            parsed_json=parsed_json,
            latency_ms=latency_ms,
            usage=usage,
            metadata={
                **request.metadata,
                "json_retry_used":
                    json_retry_used,
            },
        )
