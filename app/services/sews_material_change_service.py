from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class MaterialChangeResult:
    material_change: bool
    reasons: list[str]

class SEWSMaterialChangeService:
    def evaluate(self, *, previous: dict[str, Any] | None, current: dict[str, Any]):
        if previous is None:
            return MaterialChangeResult(True, ["initial_assessment"])
        reasons = []
        if abs(float(current.get("probability") or 0) - float(previous.get("probability") or 0)) >= 0.05:
            reasons.append("probability_changed")
        if abs(float(current.get("confidence_score") or 0) - float(previous.get("confidence_score") or 0)) >= 5:
            reasons.append("confidence_changed")
        if current.get("recommended_state") != previous.get("recommended_state"):
            reasons.append("recommended_state_changed")
        if current.get("direction") != previous.get("direction"):
            reasons.append("direction_changed")
        return MaterialChangeResult(bool(reasons), reasons)
