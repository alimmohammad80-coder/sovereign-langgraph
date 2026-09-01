from app.ai_gateway.gateway import AIGateway
from app.ai_gateway.schemas import AITaskType
from app.ai_gateway.routing import DEFAULT_ROUTES

def test_default_strategic_review_route_prefers_nvidia():
    assert DEFAULT_ROUTES[AITaskType.STRATEGIC_REVIEW].providers[0] == "NVIDIA"

def test_empty_gateway_has_no_available_providers():
    assert AIGateway([]).available_providers() == []

import json
from types import SimpleNamespace

import pytest

from app.ai_gateway.providers.gemini import GeminiProvider
from app.ai_gateway.schemas import (
    AIGatewayRequest,
    AIResponseFormat,
)


class FakeGeminiModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append(
            {
                "model": model,
                "contents": contents,
                "config": config,
            }
        )

        if not self.responses:
            raise AssertionError("No fake Gemini response remaining")

        return self.responses.pop(0)


class FakeGeminiClient:
    def __init__(self, responses):
        self.models = FakeGeminiModels(responses)


def make_response(text: str):
    return SimpleNamespace(
        text=text,
        usage_metadata=None,
    )


def make_request():
    return AIGatewayRequest(
        task_type=AITaskType.FULL_ANALYSIS,
        system_prompt="Return a structured intelligence report.",
        user_prompt='{"input":"test"}',
        response_format=AIResponseFormat.JSON,
        temperature=0.2,
        max_tokens=12000,
        metadata={
            "required_json_keys": [
                "bluf",
                "full_analysis",
            ],
        },
    )


def test_gemini_valid_json_does_not_retry(monkeypatch):
    provider = GeminiProvider(
        default_model="gemini-test",
    )

    client = FakeGeminiClient(
        [
            make_response(
                json.dumps(
                    {
                        "bluf": "Assessment",
                        "full_analysis": "Analysis",
                    }
                )
            )
        ]
    )

    monkeypatch.setattr(
        provider,
        "_client",
        lambda: client,
    )

    response = provider.generate(
        make_request()
    )

    assert len(client.models.calls) == 1
    assert response.parsed_json["bluf"] == "Assessment"
    assert response.metadata["json_retry_used"] is False


def test_gemini_retries_once_after_malformed_json(monkeypatch):
    provider = GeminiProvider(
        default_model="gemini-test",
    )

    client = FakeGeminiClient(
        [
            make_response(
                '{"bluf":"Assessment","full_analysis":"unterminated'
            ),
            make_response(
                json.dumps(
                    {
                        "bluf": "Assessment",
                        "full_analysis": "Recovered analysis",
                    }
                )
            ),
        ]
    )

    monkeypatch.setattr(
        provider,
        "_client",
        lambda: client,
    )

    response = provider.generate(
        make_request()
    )

    assert len(client.models.calls) == 2
    assert response.parsed_json["full_analysis"] == "Recovered analysis"
    assert response.metadata["json_retry_used"] is True

    retry_call = client.models.calls[1]

    assert "complete valid JSON object only" in retry_call["contents"]
    assert retry_call["config"].max_output_tokens >= 20000


def test_gemini_second_malformed_response_raises(monkeypatch):
    provider = GeminiProvider(
        default_model="gemini-test",
    )

    client = FakeGeminiClient(
        [
            make_response(
                '{"bluf":"first malformed'
            ),
            make_response(
                '{"bluf":"second malformed'
            ),
        ]
    )

    monkeypatch.setattr(
        provider,
        "_client",
        lambda: client,
    )

    with pytest.raises(
        json.JSONDecodeError
    ):
        provider.generate(
            make_request()
        )

    assert len(client.models.calls) == 2
