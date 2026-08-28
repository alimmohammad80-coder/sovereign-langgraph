from __future__ import annotations
from dataclasses import dataclass, field
from app.ai_gateway.schemas import AITaskType

@dataclass(slots=True)
class ModelRoute:
    providers: list[str] = field(default_factory=list)

DEFAULT_ROUTES = {
    AITaskType.STRATEGIC_REVIEW: ModelRoute(["NVIDIA", "GEMINI", "OPENAI"]),
    AITaskType.BLUF: ModelRoute(["NVIDIA", "GEMINI", "OPENAI"]),
    AITaskType.FULL_ANALYSIS: ModelRoute(["NVIDIA", "GEMINI"]),
    AITaskType.EXTRACTION: ModelRoute(["OPENAI", "NVIDIA"]),
    AITaskType.CLASSIFICATION: ModelRoute(["OPENAI", "NVIDIA"]),
    AITaskType.SUMMARIZATION: ModelRoute(["NVIDIA", "GEMINI", "OPENAI"]),
    AITaskType.ENTITY_RESOLUTION: ModelRoute(["OPENAI", "NVIDIA"]),
    AITaskType.HISTORICAL_ANALOG: ModelRoute(["NVIDIA", "GEMINI", "OPENAI"]),
    AITaskType.DEVILS_ADVOCATE: ModelRoute(["NVIDIA", "GEMINI", "OPENAI"]),
}
