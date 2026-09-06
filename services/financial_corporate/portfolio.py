from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional


class PortfolioRiskEngine:
    """Deterministic portfolio concentration, exposure and contagion engine."""

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    @staticmethod
    def _normalized_weights(positions: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        total = 0.0
        for item in positions:
            value = float(item.get("market_value") or 0.0)
            if value <= 0:
                continue
            row = dict(item)
            row["market_value"] = value
            rows.append(row)
            total += value
        if total <= 0:
            return []
        for row in rows:
            row["weight"] = row["market_value"] / total
        return rows

    def analyze(self, positions: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        rows = self._normalized_weights(positions)
        if not rows:
            return {"portfolio_risk_score": None, "confidence_score": 0.0, "positions": [], "methodology": "portfolio_risk_v1"}

        sector_weights = defaultdict(float)
        country_weights = defaultdict(float)
        weighted_risk = 0.0
        risk_weight_coverage = 0.0

        for row in rows:
            weight = row["weight"]
            sector_weights[str(row.get("sector") or "Unknown")] += weight
            country_weights[str(row.get("country_iso3") or "Unknown")] += weight
            if row.get("risk_score") is not None:
                weighted_risk += weight * self._clamp(float(row["risk_score"]))
                risk_weight_coverage += weight

        hhi = sum(row["weight"] ** 2 for row in rows)
        top_position = max(row["weight"] for row in rows)
        top_sector = max(sector_weights.values())
        top_country = max(country_weights.values())

        concentration_score = self._clamp(
            40.0 * min(1.0, hhi / 0.25)
            + 30.0 * min(1.0, top_position / 0.25)
            + 15.0 * min(1.0, top_sector / 0.50)
            + 15.0 * min(1.0, top_country / 0.50)
        )

        if risk_weight_coverage > 0:
            underlying_risk = self._clamp(weighted_risk / risk_weight_coverage)
            portfolio_risk = self._clamp(0.70 * underlying_risk + 0.30 * concentration_score)
        else:
            underlying_risk = None
            portfolio_risk = concentration_score

        return {
            "portfolio_risk_score": portfolio_risk,
            "underlying_weighted_risk_score": underlying_risk,
            "concentration_score": concentration_score,
            "confidence_score": self._clamp(risk_weight_coverage * 100),
            "total_market_value": round(sum(row["market_value"] for row in rows), 2),
            "position_count": len(rows),
            "hhi": round(hhi, 4),
            "largest_position_weight": round(top_position * 100, 2),
            "largest_sector_weight": round(top_sector * 100, 2),
            "largest_country_weight": round(top_country * 100, 2),
            "sector_exposure": {key: round(value * 100, 2) for key, value in sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)},
            "country_exposure": {key: round(value * 100, 2) for key, value in sorted(country_weights.items(), key=lambda x: x[1], reverse=True)},
            "positions": [
                {**row, "weight": round(row["weight"] * 100, 2)} for row in sorted(rows, key=lambda x: x["weight"], reverse=True)
            ],
            "methodology": "portfolio_risk_v1",
            "ai_generated_score": False,
        }

    def stress_test(
        self,
        positions: Iterable[Mapping[str, Any]],
        shocks: Mapping[str, float],
        shock_field: str = "entity_id",
    ) -> Dict[str, Any]:
        rows = self._normalized_weights(positions)
        total_loss_pct = 0.0
        impacts: List[Dict[str, Any]] = []

        for row in rows:
            key = str(row.get(shock_field) or "")
            shock_pct = float(shocks.get(key, 0.0))
            contribution = row["weight"] * shock_pct
            total_loss_pct += contribution
            impacts.append({
                "entity_id": row.get("entity_id"),
                "reference": key,
                "portfolio_weight": round(row["weight"] * 100, 2),
                "shock_pct": round(shock_pct, 2),
                "portfolio_impact_pct": round(contribution, 2),
            })

        return {
            "portfolio_loss_pct": round(total_loss_pct, 2),
            "post_shock_value_pct": round(100.0 + total_loss_pct, 2),
            "impacts": sorted(impacts, key=lambda item: item["portfolio_impact_pct"]),
            "shock_field": shock_field,
            "methodology": "deterministic_weighted_portfolio_stress_v1",
        }

    def contagion(
        self,
        initial_shocks: Mapping[str, float],
        edges: Iterable[Mapping[str, Any]],
        rounds: int = 3,
        damping: float = 0.65,
    ) -> Dict[str, Any]:
        """Propagate 0-100 stress across directed exposure edges.

        Edge weight is 0-1 and represents economic dependency/exposure. The method
        is deliberately deterministic and bounded; it is not a causal probability.
        """
        current = {key: self._clamp(value) for key, value in initial_shocks.items()}
        history = [dict(current)]
        edge_rows = list(edges)

        for _ in range(max(1, min(rounds, 10))):
            next_state = dict(current)
            additions = defaultdict(float)
            for edge in edge_rows:
                source = str(edge.get("source_entity_id") or "")
                target = str(edge.get("target_entity_id") or "")
                if not source or not target or source not in current:
                    continue
                weight = max(0.0, min(1.0, float(edge.get("weight") or 0.0)))
                additions[target] += current[source] * weight * damping
            for target, addition in additions.items():
                base = current.get(target, 0.0)
                next_state[target] = self._clamp(base + addition * (1.0 - base / 100.0))
            current = next_state
            history.append(dict(current))

        return {
            "final_stress": current,
            "rounds": len(history) - 1,
            "damping": damping,
            "history": history,
            "methodology": "directed_exposure_contagion_v1",
            "interpretation": "Network stress propagation, not a calibrated causal probability.",
        }
