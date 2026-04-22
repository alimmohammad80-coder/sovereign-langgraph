from collections import Counter
from app.services.curated_signals_service import generate_curated_signals

def build_dashboard_overview(limit=10, query=None):
    curated = generate_curated_signals(limit=limit, query=query)
    signals = curated.get("signals", [])

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
            "query": query
        },
        "signals": signals
    }
