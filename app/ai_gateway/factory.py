from functools import lru_cache
from app.ai_gateway.gateway import AIGateway
from app.ai_gateway.providers.openai_compatible import OpenAICompatibleProvider

@lru_cache(maxsize=1)
def get_ai_gateway() -> AIGateway:
    return AIGateway([
        OpenAICompatibleProvider(
            provider_key="NVIDIA",
            api_key_env="NVIDIA_API_KEY",
            base_url_env="NVIDIA_BASE_URL",
            default_base_url="https://integrate.api.nvidia.com/v1",
            model_env="NVIDIA_NEMOTRON_MODEL",
            default_model="nvidia/llama-3.3-nemotron-super-49b-v1",
        ),
        OpenAICompatibleProvider(
            provider_key="OPENAI",
            api_key_env="OPENAI_API_KEY",
            base_url_env="OPENAI_BASE_URL",
            default_base_url="https://api.openai.com/v1",
            model_env="OPENAI_REVIEW_MODEL",
            default_model="gpt-5-mini",
        ),
    ])
