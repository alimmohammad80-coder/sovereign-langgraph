from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from typing import Any

from openai import OpenAI

load_dotenv()


NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv(
    "NVIDIA_BASE_URL",
    "https://integrate.api.nvidia.com/v1",
)
NEMOTRON_MODEL = (
    os.getenv("NVIDIA_ULTRA_MODEL")
    or os.getenv("NEMOTRON_MODEL")
    or os.getenv("NVIDIA_MODEL")
    or "nvidia/nemotron-3-ultra-550b-a55b"
)


def nemotron_configured() -> bool:
    return bool(NVIDIA_API_KEY)


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1)
        cleaned = cleaned.replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:
        parsed = json.loads(cleaned[start : end + 1])
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Nemotron returned output that could not be parsed as JSON.")


def run_nemotron_analysis(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 1800,
) -> dict[str, Any]:
    if not nemotron_configured():
        raise RuntimeError("NVIDIA_API_KEY is not configured.")

    client = OpenAI(
        api_key=NVIDIA_API_KEY,
        base_url=NVIDIA_BASE_URL,
        timeout=90.0,
    )

    response = client.chat.completions.create(
        model=NEMOTRON_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("Nemotron returned an empty response.")

    result = _extract_json(content)

    result["_model_metadata"] = {
        "provider": "nvidia",
        "model": NEMOTRON_MODEL,
    }

    return result
