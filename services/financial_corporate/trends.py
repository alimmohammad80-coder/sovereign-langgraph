from __future__ import annotations

from typing import Any, Dict, List, Optional


class FinancialTrendAnalyzer:
    """Analyze multi-period SEC financial history without forecasting from missing data."""

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _pct_change(old: Optional[float], new: Optional[float]) -> Optional[float]:
        if old in (None, 0) or new is None:
            return None
        return round((new - old) / abs(old) * 100.0, 2)

    def analyze(self, history: Optional[Dict[str, List[Dict[str, Any]]]]) -> Dict[str, Any]:
        history = history or {}
        metric_results: Dict[str, Any] = {}
        observed_metrics = 0

        for metric in ("revenue", "net_income", "operating_income", "operating_cash_flow", "long_term_debt"):
            rows = [row for row in history.get(metric, []) if isinstance(row, dict)]
            rows = sorted(rows, key=lambda row: (row.get("period_end") or "", row.get("filed") or ""))[-5:]
            values = [self._safe_float(row.get("value")) for row in rows]
            valid = [(row, value) for row, value in zip(rows, values) if value is not None]
            if len(valid) < 2:
                metric_results[metric] = {
                    "status": "insufficient_evidence",
                    "observations": len(valid),
                    "series": rows,
                    "latest_change_pct": None,
                    "multi_period_change_pct": None,
                    "direction": "unknown",
                }
                continue

            observed_metrics += 1
            first_value = valid[0][1]
            previous_value = valid[-2][1]
            latest_value = valid[-1][1]
            latest_change = self._pct_change(previous_value, latest_value)
            multi_change = self._pct_change(first_value, latest_value)

            if latest_change is None or abs(latest_change) < 2.0:
                direction = "stable"
            elif latest_change > 0:
                direction = "rising"
            else:
                direction = "falling"

            metric_results[metric] = {
                "status": "observed",
                "observations": len(valid),
                "series": [row for row, _ in valid],
                "latest_change_pct": latest_change,
                "multi_period_change_pct": multi_change,
                "direction": direction,
            }

        signals = []
        revenue = metric_results.get("revenue") or {}
        income = metric_results.get("net_income") or {}
        cash_flow = metric_results.get("operating_cash_flow") or {}
        debt = metric_results.get("long_term_debt") or {}

        if revenue.get("latest_change_pct") is not None and revenue["latest_change_pct"] <= -10:
            signals.append({"type": "revenue_contraction", "severity": "material", "value": revenue["latest_change_pct"]})
        if income.get("latest_change_pct") is not None and income["latest_change_pct"] <= -20:
            signals.append({"type": "earnings_deterioration", "severity": "material", "value": income["latest_change_pct"]})
        if cash_flow.get("latest_change_pct") is not None and cash_flow["latest_change_pct"] <= -20:
            signals.append({"type": "cash_flow_deterioration", "severity": "material", "value": cash_flow["latest_change_pct"]})
        if debt.get("latest_change_pct") is not None and debt["latest_change_pct"] >= 20:
            signals.append({"type": "rapid_debt_growth", "severity": "material", "value": debt["latest_change_pct"]})

        return {
            "assessment_status": "complete" if observed_metrics >= 4 else ("partial" if observed_metrics else "insufficient_evidence"),
            "evidence_coverage": round(observed_metrics / 5 * 100.0, 2),
            "metrics": metric_results,
            "signals": signals,
            "methodology": "multi_period_financial_trends_v1",
            "ai_generated_score": False,
        }
