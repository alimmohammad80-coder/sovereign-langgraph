from __future__ import annotations

import ast
import json
import os
from pathlib import Path

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
        candidate = cleaned[start : end + 1]

        try:
            parsed = json.loads(candidate)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

        # Some model responses use valid Python dictionary syntax,
        # including single-quoted keys and values. literal_eval safely
        # parses literals without executing arbitrary code.
        try:
            parsed = ast.literal_eval(candidate)

            if isinstance(parsed, dict):
                return parsed

        except (
            SyntaxError,
            ValueError,
            TypeError,
        ):
            pass

    raise ValueError(
        "Nemotron returned output that could not be parsed "
        "as JSON or a dictionary literal."
    )


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
        response_format={
            "type": "json_object",
        },
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

    # Temporary local diagnostic capture. This contains model output
    # only and does not include API credentials.
    try:
        Path("/tmp/nemotron_raw_response.txt").write_text(
            str(content),
            encoding="utf-8",
        )
    except Exception:
        pass

    try:
        result = _extract_json(content)

    except (ValueError, json.JSONDecodeError):
        # Nemotron occasionally returns an analytically valid response
        # with a minor JSON formatting error. Make one bounded repair
        # request using only the original model output.
        repair_response = client.chat.completions.create(
            model=NEMOTRON_MODEL,
            temperature=0.0,
            max_tokens=max_tokens,
            response_format={
                "type": "json_object",
            },
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Repair the supplied text into valid JSON. "
                        "Preserve the original meaning and field names. "
                        "Do not add facts, analysis, commentary, markdown, "
                        "or fields that were not present. Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": content,
                },
            ],
        )

        repaired_content = (
            repair_response.choices[0].message.content
        )

        if not repaired_content:
            raise RuntimeError(
                "Nemotron JSON repair returned an empty response."
            )

        result = _extract_json(repaired_content)

        result["_json_repair_applied"] = True

    result["_model_metadata"] = {
        "provider": "nvidia",
        "model": NEMOTRON_MODEL,
    }

    return result


def run_nemotron_structured_analysis(
    *,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any],
    temperature: float = 0.1,
    max_tokens: int = 3200,
) -> dict[str, Any]:
    """
    Run Nemotron with NVIDIA guided JSON schema enforcement.

    This function is intended for outputs whose exact object shape
    and field types are part of the application contract.
    """
    if not nemotron_configured():
        raise RuntimeError(
            "NVIDIA_API_KEY is not configured."
        )

    client = OpenAI(
        api_key=NVIDIA_API_KEY,
        base_url=NVIDIA_BASE_URL,
        timeout=120.0,
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
        extra_body={
            "guided_json": json_schema,
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "Nemotron returned an empty structured response."
        )

    result = _extract_json(content)

    result["_model_metadata"] = {
        "provider": "nvidia",
        "model": NEMOTRON_MODEL,
        "structured_generation": "guided_json",
    }

    return result


def run_nemotron_text_analysis(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.15,
    max_tokens: int = 2800,
) -> str:
    """
    Run Nemotron for governed analytical prose.

    This avoids fragile JSON generation for client-facing reports.
    Deterministic scores and metadata remain controlled by Python.
    """
    if not nemotron_configured():
        raise RuntimeError(
            "NVIDIA_API_KEY is not configured."
        )

    client = OpenAI(
        api_key=NVIDIA_API_KEY,
        base_url=NVIDIA_BASE_URL,
        timeout=120.0,
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

    if not content or not str(content).strip():
        raise RuntimeError(
            "Nemotron returned an empty analytical report."
        )

    return str(content).strip()

