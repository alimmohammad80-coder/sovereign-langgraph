from __future__ import annotations

from statistics import median
from typing import Any, Dict, Iterable, List, Mapping, Optional


class SectorRelativeCalibrationEngine:
    """Calibrate company financial evidence against a supplied peer cohort.

    This engine is deliberately evidence-gated. It never fabricates sector
    benchmarks. If a peer cohort is unavailable or too small, sector-relative
    outputs remain unavailable and the base Financial Resilience score is left
    unchanged.
    """

    MIN_PEERS = 5

    @staticmethod
    def _num(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _percentile(value: float, peers: Iterable[float], higher_is_worse: bool) -> Optional[float]:
        clean = sorted(float(x) for x in peers if x is not None)
        if len(clean) < SectorRelativeCalibrationEngine.MIN_PEERS:
            return None
        below = sum(1 for x in clean if x < value)
        equal = sum(1 for x in clean if x == value)
        pct = ((below + 0.5 * equal) / len(clean)) * 100.0
        return round(pct if higher_is_worse else 100.0 - pct, 2)

    def calibrate(
        self,
        *,
        company_metrics: Mapping[str, Any],
        peer_metrics: List[Mapping[str, Any]],
        sector_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        specs = {
            "debt_to_equity": True,
            "liabilities_to_assets": True,
            "current_ratio": False,
            "interest_coverage": False,
            "net_margin": False,
            "operating_cash_flow_to_debt": False,
        }

        comparisons: Dict[str, Dict[str, Any]] = {}
        risk_percentiles: List[float] = []
        for metric, higher_is_worse in specs.items():
            company_value = self._num(company_metrics.get(metric))
            peer_values = [self._num(peer.get(metric)) for peer in peer_metrics]
            peer_values = [v for v in peer_values if v is not None]
            if company_value is None or len(peer_values) < self.MIN_PEERS:
                comparisons[metric] = {
                    "company_value": company_value,
                    "peer_count": len(peer_values),
                    "status": "insufficient_evidence",
                }
                continue
            percentile = self._percentile(company_value, peer_values, higher_is_worse)
            comparisons[metric] = {
                "company_value": round(company_value, 4),
                "peer_median": round(median(peer_values), 4),
                "peer_count": len(peer_values),
                "risk_percentile": percentile,
                "status": "observed",
            }
            if percentile is not None:
                risk_percentiles.append(percentile)

        if not risk_percentiles:
            return {
                "assessment_status": "insufficient_evidence",
                "sector_key": sector_key,
                "sector_relative_risk_score": None,
                "confidence_score": 0.0,
                "comparisons": comparisons,
                "methodology": "sector_relative_peer_percentile_v1",
                "ai_generated_score": False,
            }

        observed = len(risk_percentiles)
        score = round(sum(risk_percentiles) / observed, 2)
        confidence = round(min(100.0, (observed / len(specs)) * 70.0 + min(len(peer_metrics), 20) / 20.0 * 30.0), 2)
        return {
            "assessment_status": "complete" if observed == len(specs) else "partial",
            "sector_key": sector_key,
            "sector_relative_risk_score": score,
            "confidence_score": confidence,
            "metrics_observed": observed,
            "metrics_expected": len(specs),
            "comparisons": comparisons,
            "methodology": "sector_relative_peer_percentile_v1",
            "ai_generated_score": False,
        }
