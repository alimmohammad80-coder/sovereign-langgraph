from typing import List, Dict, Any

from app.intelligence.signals.normalizer import normalize_raw_items
from app.intelligence.signals.scorer import (
    score_signals,
    calculate_overall_warning_score,
    determine_warning_level,
)
from app.intelligence.analysis.gpt_fusion import generate_intelligence_assessment


def run_intelligence_pipeline(
    module: str,
    entity: str,
    indicator: str,
    raw_items: List[Dict[str, Any]],
) -> Dict[str, Any]:

    signals = normalize_raw_items(raw_items)
    scored_signals = score_signals(signals)

    score = calculate_overall_warning_score(scored_signals)
    level = determine_warning_level(score)

    assessment = generate_intelligence_assessment(
        module=module,
        entity=entity,
        indicator=indicator,
        score=score,
        level=level,
        signals=scored_signals,
    )

    return {
        "status": "success",
        "entity": entity,
        "module": module,
        "indicator": indicator,
        "score": score,
        "level": level,
        "signals": [s.model_dump() for s in scored_signals],
        **assessment,
    }
