from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

from supabase import Client

PRODUCT_VERSION = "sews-strategic-intelligence-product-v1.0.0"


class SEWSStrategicIntelligenceProductError(RuntimeError):
    pass


class SEWSStrategicIntelligenceProductionService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _probability_band(value: float) -> str:
        if value < 0.2:
            return "Low"
        if value < 0.4:
            return "Elevated"
        if value < 0.6:
            return "High"
        if value < 0.8:
            return "Very High"
        return "Critical"

    @staticmethod
    def _confidence_label(value: float) -> str:
        if value >= 75:
            return "High"
        if value >= 50:
            return "Moderate"
        return "Low"

    @staticmethod
    def _trend(current: float, previous: float | None) -> str:
        if previous is None:
            return "STABLE"
        change = current - previous
        if change >= 0.03:
            return "DETERIORATING"
        if change <= -0.03:
            return "IMPROVING"
        return "STABLE"

    def _problem(self, problem_key: str) -> dict[str, Any]:
        result = (
            self.db.table("sews_warning_problems")
            .select("*")
            .eq("problem_key", problem_key)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise SEWSStrategicIntelligenceProductError(
                f"Unknown warning problem: {problem_key}"
            )
        return result.data[0]

    def _latest_causal(self, problem_key: str) -> dict[str, Any]:
        result = (
            self.db.table("sews_causal_assessments")
            .select("*")
            .eq("problem_key", problem_key)
            .order("assessed_at", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise SEWSStrategicIntelligenceProductError(
                f"No causal assessment exists for {problem_key}"
            )
        return result.data[0]

    def _previous_causal(self, problem_key: str, latest_id: str) -> dict[str, Any] | None:
        rows = (
            self.db.table("sews_causal_assessments")
            .select("id,outcome_probability,confidence_score,assessed_at")
            .eq("problem_key", problem_key)
            .order("assessed_at", desc=True)
            .limit(2)
            .execute()
            .data
            or []
        )
        return next((r for r in rows if str(r.get("id")) != str(latest_id)), None)

    def _states(self, problem_key: str) -> list[dict[str, Any]]:
        return (
            self.db.table("sews_indicator_state")
            .select(
                "indicator_key,current_value,confidence,status,evidence_count,"
                "supporting_evidence_count,contradicting_evidence_count,"
                "corroborated_source_count,freshness_score,last_observed_at"
            )
            .eq("warning_problem_key", problem_key)
            .order("confidence", desc=True)
            .range(0, 9999)
            .execute()
            .data
            or []
        )

    def _evidence(self, problem_key: str) -> list[dict[str, Any]]:
        return (
            self.db.table("sews_raw_evidence")
            .select(
                "id,title,canonical_url,published_at,collected_at,"
                "country_iso3,region_key,metadata,source_id"
            )
            .contains("metadata", {"warning_problem_key": problem_key})
            .order("collected_at", desc=True)
            .limit(25)
            .execute()
            .data
            or []
        )

    @staticmethod
    def _drivers(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
        active = [
            row for row in states
            if str(row.get("status") or "").upper() == "ACTIVE"
            and row.get("current_value") is not None
        ]
        ranked = sorted(
            active,
            key=lambda row: float(row.get("current_value") or 0)
            * float(row.get("confidence") or 0),
            reverse=True,
        )
        return [
            {
                "indicator_key": row["indicator_key"],
                "current_value": float(row.get("current_value") or 0),
                "confidence": float(row.get("confidence") or 0),
                "evidence_count": int(row.get("evidence_count") or 0),
            }
            for row in ranked[:8]
        ]

    @staticmethod
    def _confidence_explanation(states: list[dict[str, Any]], confidence: float) -> dict[str, Any]:
        active = [r for r in states if str(r.get("status") or "").upper() == "ACTIVE"]
        evidence_count = sum(int(r.get("evidence_count") or 0) for r in active)
        source_count = max([int(r.get("corroborated_source_count") or 0) for r in active] or [0])
        freshness_values = [float(r.get("freshness_score") or 0) for r in active]
        contradicting = sum(int(r.get("contradicting_evidence_count") or 0) for r in active)
        supporting = sum(int(r.get("supporting_evidence_count") or 0) for r in active)
        return {
            "label": SEWSStrategicIntelligenceProductionService._confidence_label(confidence),
            "score": round(confidence, 2),
            "active_indicator_count": len(active),
            "evidence_count": evidence_count,
            "corroborated_source_count": source_count,
            "mean_freshness": round(mean(freshness_values), 2) if freshness_values else 0.0,
            "contradiction_ratio": round(contradicting / max(1, supporting + contradicting), 4),
            "remaining_uncertainty": [
                "Leadership intent and decision thresholds",
                "Potentially classified military or diplomatic activity",
                "Incomplete source coverage in low-transparency environments",
            ],
        }

    @staticmethod
    def _forecast(probability: float, horizon_days: int) -> dict[str, Any]:
        def bounded(value: float) -> float:
            return round(max(0.01, min(0.99, value)), 4)
        slope = (probability - 0.5) * 0.08
        return {
            "7_days": bounded(probability - slope * 0.35),
            "30_days": bounded(probability),
            "90_days": bounded(probability + slope),
            f"{max(180, horizon_days)}_days": bounded(probability + slope * 1.5),
            "method": "deterministic horizon extension",
        }

    @staticmethod
    def _scenarios(probability: float) -> list[dict[str, Any]]:
        worst = min(0.35, max(0.10, probability * 0.35))
        best = min(0.35, max(0.10, (1 - probability) * 0.30))
        most_likely = max(0.30, 1 - worst - best)
        total = worst + best + most_likely
        return [
            {"scenario": "Most Likely", "probability": round(most_likely / total, 4), "description": "Current conditions persist with limited but material movement along the existing trajectory."},
            {"scenario": "Worst Case", "probability": round(worst / total, 4), "description": "Multiple reinforcing indicators activate and accelerate the warning pathway."},
            {"scenario": "Best Case", "probability": round(best / total, 4), "description": "Contrary indicators strengthen and reduce the likelihood of the assessed outcome."},
        ]

    @staticmethod
    def _collection_priorities(problem: dict[str, Any], states: list[dict[str, Any]]) -> list[str]:
        insufficient = [
            row["indicator_key"] for row in states
            if str(row.get("status") or "").upper() == "INSUFFICIENT_EVIDENCE"
        ]
        priorities = [f"Collect corroborating evidence for {key}" for key in insufficient[:5]]
        priorities.extend([
            f"Monitor official statements relevant to {problem['title']}",
            "Monitor operational indicators for abrupt acceleration",
            "Seek independent confirmation for high-impact reporting",
        ])
        return priorities[:8]

    @staticmethod
    def _gaps(states: list[dict[str, Any]]) -> list[str]:
        insufficient = sum(
            1 for row in states
            if str(row.get("status") or "").upper() == "INSUFFICIENT_EVIDENCE"
        )
        return [
            f"{insufficient} mapped indicator contexts lack sufficient evidence",
            "Intent and decision thresholds remain only partially observable",
            "Open-source reporting may lag covert or classified activity",
        ]

    @staticmethod
    def _analysis(problem: dict[str, Any], probability: float, confidence: float, trend: str, drivers: list[dict[str, Any]], evidence: list[dict[str, Any]], confidence_explanation: dict[str, Any]) -> tuple[str, str, str]:
        band = SEWSStrategicIntelligenceProductionService._probability_band(probability)
        confidence_label = SEWSStrategicIntelligenceProductionService._confidence_label(confidence)
        driver_names = [item["indicator_key"] for item in drivers[:5]]
        driver_text = ", ".join(driver_names) if driver_names else "no sufficiently active indicators"
        evidence_count = len(evidence)
        bluf = (
            f"The assessed probability of {problem['title']} is {probability:.0%}, placing the warning in the {band.lower()} range. "
            f"The current trajectory is {trend.lower()}. Confidence is {confidence_label.lower()} at {confidence:.0f}%, based on "
            f"{confidence_explanation['active_indicator_count']} active indicators and {evidence_count} recent evidence records. "
            f"The strongest observed drivers are {driver_text}. The assessment should be updated if new evidence materially changes indicator activation, freshness, or corroboration."
        )
        executive = (
            f"{problem['title']} remains assessed at {probability:.0%} probability over the stated {problem.get('horizon_days') or 90}-day horizon. "
            f"The latest causal assessment indicates a {trend.lower()} trajectory with {confidence_label.lower()} confidence. "
            f"The current judgment is driven primarily by {driver_text}. Collection should prioritize unresolved indicator gaps and independent corroboration of high-impact reporting."
        )
        sections = [
            ("Current Situation", f"The latest SEWS causal assessment places the probability of {problem['title']} at {probability:.1%}. This is a {band.lower()} warning level relative to the configured base rate and the current evidence picture. The assessed direction is {trend.lower()}. The judgment is bounded by the warning hypothesis: {problem.get('hypothesis') or problem.get('title') or '' ''}"),
            ("Key Drivers", f"The most influential active indicators are {driver_text}. These indicators matter because they represent observable conditions within the causal pathway rather than isolated news events. Their effect is moderated by source reliability, freshness, corroboration, and contradiction. Indicators without sufficient evidence do not contribute artificial confidence."),
            ("Evidence Assessment", f"The product draws on {evidence_count} recent raw evidence records and {confidence_explanation['active_indicator_count']} active indicator states. Aggregate confidence is {confidence:.1f}%. Mean evidence freshness is {confidence_explanation['mean_freshness']:.1f}%, and the contradiction ratio is {confidence_explanation['contradiction_ratio']:.1%}. The evidence base is therefore adequate for a directional judgment but may remain incomplete where reporting access is limited or state intent is not directly observable."),
            ("Causal Interpretation", "SEWS evaluates how indicator activation propagates through precursor, acceleration, trigger, mitigation, and outcome nodes. The resulting probability is not a simple count of articles. It reflects the interaction of mapped indicators, their confidence, their freshness, and the configured causal edges. This structure reduces the risk that repetitive or low-quality reporting dominates the assessment."),
            ("Forecast", f"Absent a material change in the evidence, the warning is expected to remain broadly {trend.lower()} over the near term. A sharp increase would require stronger trigger indicators, greater cross-source corroboration, or activation of connected warning pathways. A decline would require credible contrary evidence, de-escalatory action, or sustained weakening of the current drivers."),
            ("Strategic Implications", f"If the assessed outcome occurs, implications will extend beyond the immediate {problem.get('domain') or 'strategic'} domain through linked economic, political, security, and supply-chain pathways. Decision-makers should use the current probability as a planning judgment, not as certainty. The most valuable next step is targeted collection against the largest evidence gaps and close monitoring for material changes."),
        ]
        return bluf, executive, "\n\n".join(f"{title}\n{text}" for title, text in sections)

    def generate(self, problem_key: str, *, persist: bool = True) -> dict[str, Any]:
        problem = self._problem(problem_key)
        causal = self._latest_causal(problem_key)
        previous = self._previous_causal(problem_key, str(causal["id"]))
        states = self._states(problem_key)
        evidence = self._evidence(problem_key)
        probability = float(causal["outcome_probability"])
        confidence = float(causal.get("confidence_score") or 0)
        previous_probability = float(previous["outcome_probability"]) if previous and previous.get("outcome_probability") is not None else None
        trend = self._trend(probability, previous_probability)
        drivers = self._drivers(states)
        confidence_explanation = self._confidence_explanation(states, confidence)
        forecast = self._forecast(probability, int(problem.get("horizon_days") or 90))
        scenarios = self._scenarios(probability)
        gaps = self._gaps(states)
        priorities = self._collection_priorities(problem, states)
        bluf, executive, complete = self._analysis(problem, probability, confidence, trend, drivers, evidence, confidence_explanation)

        countries = problem.get("countries") or []
        country_iso3 = countries[0] if isinstance(countries, list) and countries else None
        product = {
            "warning_problem_key": problem_key,
            "causal_assessment_id": causal["id"],
            "warning_assessment_id": causal.get("warning_assessment_id"),
            "country_iso3": country_iso3,
            "region_key": problem.get("region"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "probability": probability,
            "confidence": confidence,
            "trend": trend,
            "bluf": bluf,
            "executive_summary": executive,
            "complete_analysis": complete,
            "key_drivers": drivers,
            "confidence_explanation": confidence_explanation,
            "evidence_summary": [
                {"id": row.get("id"), "title": row.get("title"), "url": row.get("canonical_url"), "published_at": row.get("published_at"), "collected_at": row.get("collected_at")}
                for row in evidence[:15]
            ],
            "forecast": forecast,
            "scenarios": scenarios,
            "intelligence_gaps": gaps,
            "collection_priorities": priorities,
            "metadata": {
                "product_version": PRODUCT_VERSION,
                "previous_probability": previous_probability,
                "domain": problem.get("domain"),
                "horizon_days": problem.get("horizon_days"),
            },
        }
        if persist:
            existing_rows = (
                self.db.table("sews_intelligence_products")
                .select("id")
                .eq("warning_problem_key", problem_key)
                .eq(
                    "causal_assessment_id",
                    str(causal["id"]),
                )
                .limit(1)
                .execute()
                .data
                or []
            )

            if existing_rows:
                saved_rows = (
                    self.db.table("sews_intelligence_products")
                    .update(product)
                    .eq("id", existing_rows[0]["id"])
                    .execute()
                    .data
                    or []
                )
            else:
                saved_rows = (
                    self.db.table("sews_intelligence_products")
                    .insert(product)
                    .execute()
                    .data
                    or []
                )

            if not saved_rows:
                raise SEWSStrategicIntelligenceProductError(
                    "Product persistence returned no row."
                )

            product["id"] = saved_rows[0]["id"]

        return product
