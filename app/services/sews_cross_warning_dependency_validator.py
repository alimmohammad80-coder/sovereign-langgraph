from __future__ import annotations

from typing import Any

from supabase import Client


VALIDATION_VERSION = "sews-cross-warning-validation-v1"


def pair_key(first: str, second: str) -> tuple[str, str]:
    return tuple(sorted((first, second)))


VALIDATED_RULES: dict[tuple[str, str], dict[str, Any]] = {
    pair_key("WP-TWN-BLOCKADE", "WP-SEMICONDUCTOR-SHOCK"): {
        "source": "WP-TWN-BLOCKADE",
        "target": "WP-SEMICONDUCTOR-SHOCK",
        "relationship_type": "CAUSES",
        "transmission_strength": 0.92,
        "conditional_probability": 0.88,
        "lag_hours": 12,
        "rationale": (
            "A blockade or sustained quarantine of Taiwan would directly "
            "disrupt semiconductor production, exports, logistics, and access."
        ),
    },
    pair_key("WP-IRN-ISR-ESCALATION", "WP-HORMUZ-CLOSURE"): {
        "source": "WP-IRN-ISR-ESCALATION",
        "target": "WP-HORMUZ-CLOSURE",
        "relationship_type": "AMPLIFIES",
        "transmission_strength": 0.78,
        "conditional_probability": 0.62,
        "lag_hours": 12,
        "rationale": (
            "Regional military escalation involving Iran materially increases "
            "the risk of interdiction, mining, attacks, or closure threats in Hormuz."
        ),
    },
    pair_key("WP-IRN-ISR-ESCALATION", "WP-RED-SEA-SHIPPING"): {
        "source": "WP-IRN-ISR-ESCALATION",
        "target": "WP-RED-SEA-SHIPPING",
        "relationship_type": "AMPLIFIES",
        "transmission_strength": 0.67,
        "conditional_probability": 0.56,
        "lag_hours": 24,
        "rationale": (
            "Regional escalation can increase proxy attacks, maritime threats, "
            "rerouting, and insurance pressure affecting Red Sea shipping."
        ),
    },
    pair_key("WP-IRN-ISR-ESCALATION", "WP-ENERGY-PRICE-SPIKE"): {
        "source": "WP-IRN-ISR-ESCALATION",
        "target": "WP-ENERGY-PRICE-SPIKE",
        "relationship_type": "AMPLIFIES",
        "transmission_strength": 0.74,
        "conditional_probability": 0.66,
        "lag_hours": 6,
        "rationale": (
            "Sustained Iran–Israel escalation raises energy supply-risk premiums "
            "and the probability of physical disruption."
        ),
    },
    pair_key("WP-HORMUZ-CLOSURE", "WP-ENERGY-PRICE-SPIKE"): {
        "source": "WP-HORMUZ-CLOSURE",
        "target": "WP-ENERGY-PRICE-SPIKE",
        "relationship_type": "CAUSES",
        "transmission_strength": 0.95,
        "conditional_probability": 0.91,
        "lag_hours": 3,
        "rationale": (
            "Severe disruption of Hormuz would directly constrain oil and LNG "
            "flows and produce an immediate global energy-price shock."
        ),
    },
    pair_key("WP-HORMUZ-CLOSURE", "WP-EM-SOVEREIGN-DEBT"): {
        "source": "WP-HORMUZ-CLOSURE",
        "target": "WP-EM-SOVEREIGN-DEBT",
        "relationship_type": "TRANSMITS",
        "transmission_strength": 0.58,
        "conditional_probability": 0.52,
        "lag_hours": 168,
        "rationale": (
            "A prolonged Hormuz disruption can transmit through import costs, "
            "inflation, currency pressure, and fiscal stress into sovereign debt risk."
        ),
    },
    pair_key("WP-RED-SEA-SHIPPING", "WP-SUEZ-DISRUPTION"): {
        "source": "WP-RED-SEA-SHIPPING",
        "target": "WP-SUEZ-DISRUPTION",
        "relationship_type": "AMPLIFIES",
        "transmission_strength": 0.76,
        "conditional_probability": 0.68,
        "lag_hours": 12,
        "rationale": (
            "Sustained Red Sea insecurity can reduce traffic, force rerouting, "
            "and create operational disruption affecting the Suez corridor."
        ),
    },
    pair_key("WP-RED-SEA-SHIPPING", "WP-ENERGY-PRICE-SPIKE"): {
        "source": "WP-RED-SEA-SHIPPING",
        "target": "WP-ENERGY-PRICE-SPIKE",
        "relationship_type": "TRANSMITS",
        "transmission_strength": 0.55,
        "conditional_probability": 0.48,
        "lag_hours": 48,
        "rationale": (
            "Shipping disruption can increase delivery delays, freight costs, "
            "insurance premiums, and short-term energy-market risk premiums."
        ),
    },
    pair_key("WP-UKR-FRONT-DETERIORATION", "WP-RUS-NATO-SPILLOVER"): {
        "source": "WP-UKR-FRONT-DETERIORATION",
        "target": "WP-RUS-NATO-SPILLOVER",
        "relationship_type": "AMPLIFIES",
        "transmission_strength": 0.72,
        "conditional_probability": 0.57,
        "lag_hours": 24,
        "rationale": (
            "Major deterioration on the Ukrainian front increases escalation, "
            "miscalculation, cross-border strike, and NATO-force exposure risks."
        ),
    },
    pair_key("WP-RUS-NATO-SPILLOVER", "WP-ENERGY-PRICE-SPIKE"): {
        "source": "WP-RUS-NATO-SPILLOVER",
        "target": "WP-ENERGY-PRICE-SPIKE",
        "relationship_type": "AMPLIFIES",
        "transmission_strength": 0.61,
        "conditional_probability": 0.54,
        "lag_hours": 24,
        "rationale": (
            "Direct Russia–NATO spillover would increase disruption and sanctions "
            "risk across European and global energy markets."
        ),
    },
    pair_key("WP-ENERGY-PRICE-SPIKE", "WP-FOOD-SECURITY-SHOCK"): {
        "source": "WP-ENERGY-PRICE-SPIKE",
        "target": "WP-FOOD-SECURITY-SHOCK",
        "relationship_type": "TRANSMITS",
        "transmission_strength": 0.72,
        "conditional_probability": 0.65,
        "lag_hours": 336,
        "rationale": (
            "Higher energy, fertilizer, transport, storage, and production costs "
            "transmit into food affordability and availability risks."
        ),
    },
    pair_key("WP-EM-SOVEREIGN-DEBT", "WP-FOOD-SECURITY-SHOCK"): {
        "source": "WP-EM-SOVEREIGN-DEBT",
        "target": "WP-FOOD-SECURITY-SHOCK",
        "relationship_type": "AMPLIFIES",
        "transmission_strength": 0.62,
        "conditional_probability": 0.55,
        "lag_hours": 336,
        "rationale": (
            "Sovereign debt distress can constrain food imports, subsidies, "
            "humanitarian spending, currency stability, and public distribution."
        ),
    },
    pair_key("WP-CHN-FINANCIAL-STRESS", "WP-SEMICONDUCTOR-SHOCK"): {
        "source": "WP-CHN-FINANCIAL-STRESS",
        "target": "WP-SEMICONDUCTOR-SHOCK",
        "relationship_type": "AMPLIFIES",
        "transmission_strength": 0.42,
        "conditional_probability": 0.38,
        "lag_hours": 336,
        "rationale": (
            "Severe Chinese financial stress may weaken industrial demand, credit, "
            "investment, supplier liquidity, and semiconductor-sector stability."
        ),
    },
}


class SEWSCrossWarningDependencyValidator:
    def __init__(self, db: Client):
        self.db = db

    def validate_all(self) -> dict[str, Any]:
        rows = (
            self.db.table("sews_warning_dependencies")
            .select("*")
            .eq("active", True)
            .execute()
            .data
            or []
        )

        validated = 0
        retained_unvalidated = 0

        for row in rows:
            key = pair_key(
                row["source_problem_key"],
                row["target_problem_key"],
            )
            rule = VALIDATED_RULES.get(key)

            metadata = dict(row.get("metadata") or {})
            metadata["validation_version"] = VALIDATION_VERSION

            if rule is None:
                metadata["validation_note"] = (
                    "No sufficiently defensible deterministic causal direction "
                    "has been assigned. Relationship remains related and unvalidated."
                )

                (
                    self.db.table("sews_warning_dependencies")
                    .update(
                        {
                            "relationship_type": "RELATED",
                            "direction_status": "UNVALIDATED",
                            "transmission_strength": 0,
                            "conditional_probability": None,
                            "lag_hours": 0,
                            "metadata": metadata,
                        }
                    )
                    .eq("id", row["id"])
                    .execute()
                )

                retained_unvalidated += 1
                continue

            metadata["validation_method"] = "CURATED_DETERMINISTIC_BASELINE"

            (
                self.db.table("sews_warning_dependencies")
                .update(
                    {
                        "source_problem_key": rule["source"],
                        "target_problem_key": rule["target"],
                        "relationship_type": rule["relationship_type"],
                        "direction_status": "VALIDATED",
                        "transmission_strength": rule[
                            "transmission_strength"
                        ],
                        "conditional_probability": rule[
                            "conditional_probability"
                        ],
                        "lag_hours": rule["lag_hours"],
                        "rationale": rule["rationale"],
                        "metadata": metadata,
                    }
                )
                .eq("id", row["id"])
                .execute()
            )

            validated += 1

        return {
            "relationships_considered": len(rows),
            "relationships_validated": validated,
            "relationships_left_unvalidated": retained_unvalidated,
            "validation_version": VALIDATION_VERSION,
        }
