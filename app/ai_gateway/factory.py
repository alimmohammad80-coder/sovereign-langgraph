from functools import lru_cache

from app.ai_gateway.gateway import AIGateway
from app.ai_gateway.providers.openai_compatible import (
    OpenAICompatibleProvider,
)
from app.ai_gateway.providers.gemini import (
    GeminiProvider,
)


@lru_cache(maxsize=1)
def get_ai_gateway() -> AIGateway:

    return AIGateway(
        [
            OpenAICompatibleProvider(
                provider_key="NVIDIA",
                api_key_env="NVIDIA_API_KEY",
                base_url_env="NVIDIA_BASE_URL",
                default_base_url=(
                    "https://integrate.api.nvidia.com/v1"
                ),
                model_env="NVIDIA_NEMOTRON_MODEL",
                default_model=(
                    "nvidia/nemotron-3-ultra-550b-a55b"
                ),
                timeout_env="NVIDIA_TIMEOUT_SECONDS",
                default_timeout_seconds=420.0,
            ),

            GeminiProvider(
                default_model="gemini-3.1-pro-preview",
            ),

            OpenAICompatibleProvider(
                provider_key="OPENAI",
                api_key_env="OPENAI_API_KEY",
                base_url_env="OPENAI_BASE_URL",
                default_base_url=(
                    "https://api.openai.com/v1"
                ),
                model_env="OPENAI_REVIEW_MODEL",
                default_model="gpt-5-mini",
                timeout_env="OPENAI_TIMEOUT_SECONDS",
                default_timeout_seconds=120.0,
            ),
        ]
    )
