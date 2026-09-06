from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"


class FREDCreditConditionsCollector:
    """Collect macro/credit series from FRED's public CSV endpoint."""

    SERIES = {
        "baa_10y_spread": "BAA10Y",
        "aaa_10y_spread": "AAA10Y",
        "ten_year_minus_fed_funds": "T10YFF",
        "effective_fed_funds": "EFFR",
        "ten_year_treasury": "DGS10",
    }

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    def fetch_series(self, series_id: str, limit: int = 120) -> Dict[str, Any]:
        response = requests.get(
            FRED_CSV_BASE,
            params={"id": series_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        observations: List[Dict[str, Any]] = []
        value_key = series_id
        for row in reader:
            raw = row.get(value_key)
            if raw in (None, "", "."):
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            observations.append({"date": row.get("DATE"), "value": value})
        if limit > 0:
            observations = observations[-limit:]
        return {
            "provider": "fred",
            "series_id": series_id,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "observations": observations,
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
        }

    def snapshot(self) -> Dict[str, Any]:
        series: Dict[str, Any] = {}
        for key, series_id in self.SERIES.items():
            try:
                series[key] = self.fetch_series(series_id)
            except Exception as exc:
                series[key] = {
                    "provider": "fred",
                    "series_id": series_id,
                    "error": str(exc),
                    "observations": [],
                }
        return {
            "provider": "fred",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "series": series,
        }


class CreditConditionsAnalyzer:
    """Deterministic system-level funding and credit stress model."""

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    @staticmethod
    def _latest(series_payload: Dict[str, Any]) -> Optional[float]:
        observations = series_payload.get("observations") or []
        if not observations:
            return None
        try:
            return float(observations[-1]["value"])
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _change(series_payload: Dict[str, Any], periods: int = 20) -> Optional[float]:
        observations = series_payload.get("observations") or []
        if len(observations) <= periods:
            return None
        try:
            return float(observations[-1]["value"]) - float(observations[-periods - 1]["value"])
        except (KeyError, TypeError, ValueError):
            return None

    def analyze(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        series = snapshot.get("series") or {}
        baa = self._latest(series.get("baa_10y_spread") or {})
        aaa = self._latest(series.get("aaa_10y_spread") or {})
        curve = self._latest(series.get("ten_year_minus_fed_funds") or {})
        effr = self._latest(series.get("effective_fed_funds") or {})
        baa_change = self._change(series.get("baa_10y_spread") or {}, 20)

        components: Dict[str, float] = {}
        if baa is not None:
            components["baa_spread_risk"] = self._clamp(max(0.0, (baa - 1.0) / 4.0) * 100.0)
        if aaa is not None:
            components["aaa_spread_risk"] = self._clamp(max(0.0, (aaa - 0.5) / 2.5) * 100.0)
        if curve is not None:
            components["curve_inversion_risk"] = self._clamp(max(0.0, -curve / 2.0) * 100.0)
        if effr is not None:
            components["policy_rate_risk"] = self._clamp(max(0.0, (effr - 2.0) / 5.0) * 100.0)
        if baa_change is not None:
            components["spread_momentum_risk"] = self._clamp(max(0.0, baa_change / 1.0) * 100.0)

        weights = {
            "baa_spread_risk": 0.35,
            "aaa_spread_risk": 0.15,
            "curve_inversion_risk": 0.20,
            "policy_rate_risk": 0.15,
            "spread_momentum_risk": 0.15,
        }
        available_weight = sum(weights[key] for key in components)
        score = 50.0 if available_weight == 0 else sum(
            components[key] * weights[key] for key in components
        ) / available_weight

        confidence = self._clamp((len(components) / len(weights)) * 100.0)
        return {
            "credit_conditions_score": self._clamp(score),
            "confidence_score": confidence,
            "methodology": "system_credit_conditions_v1",
            "latest": {
                "baa_10y_spread": baa,
                "aaa_10y_spread": aaa,
                "ten_year_minus_fed_funds": curve,
                "effective_fed_funds": effr,
                "baa_20d_change": baa_change,
            },
            "components": components,
            "weights": weights,
            "ai_generated_score": False,
        }
