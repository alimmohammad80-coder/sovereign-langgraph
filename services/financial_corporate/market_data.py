from __future__ import annotations

import math
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"


class MarketDataConfigurationError(RuntimeError):
    pass


class AlphaVantageMarketCollector:
    """Optional global equity market-data adapter.

    The adapter intentionally returns normalized observations only. The downstream
    market-stress engine owns all risk calculations so a vendor cannot directly
    determine a Sovereign Intelligence risk score.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = 20) -> None:
        self.api_key = (api_key or os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            raise MarketDataConfigurationError("ALPHA_VANTAGE_API_KEY is not configured")
        params = dict(params)
        params["apikey"] = self.api_key
        response = requests.get(ALPHA_VANTAGE_BASE, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected market-data response")
        if data.get("Error Message"):
            raise ValueError(str(data["Error Message"]))
        if data.get("Note"):
            raise RuntimeError(str(data["Note"]))
        return data

    def daily_prices(self, symbol: str, outputsize: str = "compact") -> Dict[str, Any]:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        raw = self._get({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
        })
        series = raw.get("Time Series (Daily)") or {}
        observations: List[Dict[str, Any]] = []
        for date, row in series.items():
            if not isinstance(row, dict):
                continue
            try:
                observations.append({
                    "date": date,
                    "open": float(row.get("1. open")),
                    "high": float(row.get("2. high")),
                    "low": float(row.get("3. low")),
                    "close": float(row.get("4. close")),
                    "volume": float(row.get("5. volume")),
                })
            except (TypeError, ValueError):
                continue
        observations.sort(key=lambda item: item["date"])
        return {
            "provider": "alpha_vantage",
            "symbol": symbol,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "observations": observations,
            "source": "TIME_SERIES_DAILY",
        }


class MarketStressAnalyzer:
    """Deterministic equity-market stress model from daily close observations."""

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    @staticmethod
    def _returns(closes: List[float]) -> List[float]:
        returns: List[float] = []
        for previous, current in zip(closes, closes[1:]):
            if previous <= 0:
                continue
            returns.append((current / previous) - 1.0)
        return returns

    @staticmethod
    def _max_drawdown(closes: List[float]) -> float:
        if not closes:
            return 0.0
        peak = closes[0]
        max_dd = 0.0
        for value in closes:
            peak = max(peak, value)
            if peak > 0:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
        return max_dd

    @staticmethod
    def _period_return(closes: List[float], periods: int) -> Optional[float]:
        if len(closes) <= periods or closes[-periods - 1] <= 0:
            return None
        return (closes[-1] / closes[-periods - 1]) - 1.0

    def analyze(self, market_payload: Dict[str, Any]) -> Dict[str, Any]:
        observations = market_payload.get("observations") or []
        closes = [float(item["close"]) for item in observations if item.get("close") is not None]
        if len(closes) < 3:
            return {
                "market_stress_score": 50.0,
                "confidence_score": 10.0,
                "methodology": "equity_market_stress_v1",
                "reason": "insufficient_price_history",
            }

        daily_returns = self._returns(closes)
        annualized_vol = statistics.pstdev(daily_returns) * math.sqrt(252) if len(daily_returns) > 1 else 0.0
        max_drawdown = self._max_drawdown(closes)
        return_5d = self._period_return(closes, 5)
        return_21d = self._period_return(closes, 21)
        return_63d = self._period_return(closes, 63)

        volatility_risk = self._clamp((annualized_vol / 0.60) * 100.0)
        drawdown_risk = self._clamp((max_drawdown / 0.50) * 100.0)
        momentum_21d_risk = self._clamp(max(0.0, -(return_21d or 0.0)) / 0.25 * 100.0)
        momentum_63d_risk = self._clamp(max(0.0, -(return_63d or 0.0)) / 0.40 * 100.0)

        score = self._clamp(
            volatility_risk * 0.30
            + drawdown_risk * 0.35
            + momentum_21d_risk * 0.20
            + momentum_63d_risk * 0.15
        )
        confidence = self._clamp(min(100.0, (len(closes) / 100.0) * 100.0))

        return {
            "market_stress_score": score,
            "confidence_score": confidence,
            "methodology": "equity_market_stress_v1",
            "metrics": {
                "latest_close": closes[-1],
                "annualized_volatility": round(annualized_vol, 6),
                "max_drawdown": round(max_drawdown, 6),
                "return_5d": None if return_5d is None else round(return_5d, 6),
                "return_21d": None if return_21d is None else round(return_21d, 6),
                "return_63d": None if return_63d is None else round(return_63d, 6),
            },
            "components": {
                "volatility_risk": volatility_risk,
                "drawdown_risk": drawdown_risk,
                "momentum_21d_risk": momentum_21d_risk,
                "momentum_63d_risk": momentum_63d_risk,
            },
            "weights": {
                "volatility_risk": 0.30,
                "drawdown_risk": 0.35,
                "momentum_21d_risk": 0.20,
                "momentum_63d_risk": 0.15,
            },
            "ai_generated_score": False,
        }
