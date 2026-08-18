from __future__ import annotations

import json

from app.services.conflict_intelligence.conflict_forecast_backtester import (
    ConflictForecastBacktester,
)

result = (
    ConflictForecastBacktester()
    .run()
)

print("=" * 70)
print("CONFLICT FORECAST BACKTEST")
print("=" * 70)

print(
    json.dumps(
        result,
        indent=2,
    )
)
