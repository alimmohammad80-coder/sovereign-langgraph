from __future__ import annotations

from typing import Iterable

from app.ai_gateway.providers.base import (
    BaseAIProvider,
)
from app.ai_gateway.routing import (
    DEFAULT_ROUTES,
)
from app.ai_gateway.schemas import (
    AIGatewayRequest,
    AIGatewayResponse,
)


class AIGatewayError(RuntimeError):
    pass


class AIGateway:

    def __init__(
        self,
        providers: Iterable[BaseAIProvider],
    ) -> None:

        self._providers = {
            p.provider_key.upper(): p
            for p in providers
        }

    def available_providers(
        self,
    ) -> list[str]:

        return sorted(
            key
            for key, provider
            in self._providers.items()
            if provider.is_configured()
        )

    def _candidates(
        self,
        request: AIGatewayRequest,
    ) -> list[str]:

        route = DEFAULT_ROUTES.get(
            request.task_type
        )

        routed = (
            list(route.providers)
            if route
            else []
        )

        if not request.preferred_provider:
            return routed

        preferred = (
            request.preferred_provider
            .upper()
        )

        return [
            preferred,
            *[
                provider
                for provider in routed
                if provider != preferred
            ],
        ]

    def generate(
        self,
        request: AIGatewayRequest,
    ) -> AIGatewayResponse:

        candidates = self._candidates(
            request
        )

        errors: list[str] = []

        first_provider = (
            candidates[0]
            if candidates
            else None
        )

        for provider_key in candidates:

            provider = self._providers.get(
                provider_key
            )

            if provider is None:
                errors.append(
                    f"{provider_key}: not registered"
                )
                continue

            if not provider.is_configured():
                errors.append(
                    f"{provider_key}: not configured"
                )
                continue

            #
            # preferred_model belongs to the explicitly
            # requested provider. Never send an NVIDIA
            # model name to Gemini/OpenAI fallback.
            #
            provider_request = (
                request.model_copy(
                    update={
                        "preferred_provider":
                            provider_key,

                        "preferred_model": (
                            request.preferred_model
                            if (
                                provider_key
                                == first_provider
                            )
                            else None
                        ),
                    }
                )
            )

            try:
                response = provider.generate(
                    provider_request
                )

                metadata = dict(
                    response.metadata
                    or {}
                )

                metadata.update(
                    {
                        "fallback_used":
                            (
                                provider_key
                                != first_provider
                            ),

                        "primary_provider":
                            first_provider,

                        "selected_provider":
                            provider_key,

                        "failed_attempts":
                            list(errors),
                    }
                )

                return response.model_copy(
                    update={
                        "metadata":
                            metadata
                    }
                )

            except Exception as exc:
                errors.append(
                    (
                        f"{provider_key}: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )
                )

        raise AIGatewayError(
            "No provider completed the request. "
            + " | ".join(errors)
        )
