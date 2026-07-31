from __future__ import annotations
from dataclasses import dataclass, field
from app.ai_gateway.schemas import AITaskType

@dataclass(slots=True)
class ModelRoute:
    providers: list[str] = field(default_factory=list)

DEFAULT_ROUTES = {
    AITaskType.STRATEGIC_REVIEW: ModelRoute(["NVIDIA", "OPENAI"]),
    AITaskType.BLUF: ModelRoute(["NVIDIA", "OPENAI"]),
    AITaskType.FULL_ANALYSIS: ModelRoute(["NVIDIA", "OPENAI"]),
    AITaskType.EXTRACTION: ModelRoute(["OPENAI", "NVIDIA"]),
    AITaskType.CLASSIFICATION: ModelRoute(["OPENAI", "NVIDIA"]),
    AITaskType.SUMMARIZATION: ModelRoute(["NVIDIA", "OPENAI"]),
    AITaskType.ENTITY_RESOLUTION: ModelRoute(["OPENAI", "NVIDIA"]),
    AITaskType.HISTORICAL_ANALOG: ModelRoute(["NVIDIA", "OPENAI"]),
    AITaskType.DEVILS_ADVOCATE: ModelRoute(["NVIDIA", "OPENAI"]),
}
