# Sovereign Intelligence AI Gateway

This centralizes model access for SEWS and the rest of the platform. It reuses
the existing NVIDIA/Nemotron and OpenAI environment variables; no second
Nemotron configuration is required.

## Existing variables reused

- NVIDIA_API_KEY
- NVIDIA_BASE_URL
- NVIDIA_NEMOTRON_MODEL
- OPENAI_API_KEY
- OPENAI_BASE_URL
- OPENAI_REVIEW_MODEL

## Example

```python
from app.ai_gateway import (
    AIGatewayRequest,
    AIResponseFormat,
    AITaskType,
    get_ai_gateway,
)

response = get_ai_gateway().generate(
    AIGatewayRequest(
        task_type=AITaskType.STRATEGIC_REVIEW,
        system_prompt="...",
        user_prompt="...",
        response_format=AIResponseFormat.JSON,
    )
)
```
