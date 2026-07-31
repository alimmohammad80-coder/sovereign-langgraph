from __future__ import annotations
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class AITaskType(StrEnum):
    STRATEGIC_REVIEW = "STRATEGIC_REVIEW"
    BLUF = "BLUF"
    FULL_ANALYSIS = "FULL_ANALYSIS"
    EXTRACTION = "EXTRACTION"
    CLASSIFICATION = "CLASSIFICATION"
    SUMMARIZATION = "SUMMARIZATION"
    ENTITY_RESOLUTION = "ENTITY_RESOLUTION"
    HISTORICAL_ANALOG = "HISTORICAL_ANALOG"
    DEVILS_ADVOCATE = "DEVILS_ADVOCATE"

class AIResponseFormat(StrEnum):
    TEXT = "TEXT"
    JSON = "JSON"

class AIGatewayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_type: AITaskType
    system_prompt: str
    user_prompt: str
    preferred_provider: str | None = None
    preferred_model: str | None = None
    response_format: AIResponseFormat = AIResponseFormat.TEXT
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=200000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class AIGatewayResponse(BaseModel):
    provider: str
    model: str
    task_type: AITaskType
    content: str
    parsed_json: dict[str, Any] | list[Any] | None = None
    latency_ms: int
    usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
