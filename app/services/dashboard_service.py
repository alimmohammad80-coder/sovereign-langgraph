from collections import Counter
from typing import Any, Dict, List, Optional

from app.services.curated_signals_service import generate_curated_signals


def _safe_list(value: Any) -> List[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _build_snapshot(signals: List[dict]) -> str:
    if not signals:
        return "No high-confidence strategic signals available."

    categories = [s.get("category") for s in signals if s.get("category")]
    if not categories:
        return "Recent reporting is mixed and does not yet show a single dominant theme."

    top = Counter(categories).most_common(2)
    if len(top) == 1:
        return f"Current reporting is dominated by {top[0][0].lower()} developments."
    return f"Current reporting is led by {top[0][0].lower()} and {top[1][0].lower()} developments."


def build_dashboard_overview(limit: int = 10, query: Optional[str] = None) -> Dict[str, Any]:
    try:
        curated = generate_curated_signals(limit=limit, query=query)

        signals = _safe_list(curated.get("signals"))
        error = curated.get("error")

        category_counts = Counter()
        country_counts = Counter()

        for signal in signals:
            category = signal.get("category")
            country = signal.get("country")

            if category:
                category_counts[category] += 1
            if country:
                country_counts[country] += 1

        return {
            "summary": {
                "signal_count": len(signals),
                "top_categories": [
                    {"name": k, "count": v} for k, v in category_counts.most_common(5)
                ],
                "top_countries": [
                    {"name": k, "count": v} for k, v in country_counts.most_common(5)
                ],
                "query": query,
                "analytic_snapshot": _build_snapshot(signals),
            },
            "signals": signals,
            "error": error,
        }

    except Exception as e:
        return {
            "summary": {
                "signal_count": 0,
                "top_categories": [],
                "top_countries": [],
                "query": query,
                "analytic_snapshot": "Dashboard generation failed.",
            },
            "signals": [],
            "error": str(e),
        }
