from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TAXONOMY_PATH = Path(
    "app/data/sews_global_indicator_taxonomy.json"
)

OUTPUT_PATH = Path(
    "app/data/sews_global_indicator_library.json"
)

INDICATOR_CLASSES = (
    "PRECURSOR",
    "ACCELERANT",
    "TRIGGER",
    "CONTRA",
)

CLASS_CONFIG: dict[str, dict[str, Any]] = {
    "PRECURSOR": {
        "name_suffix": "Emerging Signal",
        "description_prefix": (
            "Early evidence indicating that conditions may be developing"
        ),
        "default_weight": 0.85,
        "default_relevance": 70,
        "expected_direction": "INCREASE",
        "measurement_type": "INDEX",
        "collection_priority": 3,
    },
    "ACCELERANT": {
        "name_suffix": "Acceleration Signal",
        "description_prefix": (
            "Evidence that an existing risk trajectory is intensifying"
        ),
        "default_weight": 1.15,
        "default_relevance": 80,
        "expected_direction": "INCREASE",
        "measurement_type": "INDEX",
        "collection_priority": 2,
    },
    "TRIGGER": {
        "name_suffix": "Trigger Event",
        "description_prefix": (
            "High-impact evidence capable of moving the warning problem "
            "into an immediate escalation state"
        ),
        "default_weight": 1.50,
        "default_relevance": 90,
        "expected_direction": "PRESENCE",
        "measurement_type": "BOOLEAN",
        "collection_priority": 1,
    },
    "CONTRA": {
        "name_suffix": "Contrary Evidence",
        "description_prefix": (
            "Evidence indicating restraint, stabilization, recovery, "
            "de-escalation, or absence of the expected risk condition"
        ),
        "default_weight": 1.00,
        "default_relevance": 80,
        "expected_direction": "DECREASE",
        "measurement_type": "INDEX",
        "collection_priority": 2,
    },
}


def build_indicator_key(
    subcategory_key: str,
    indicator_class: str,
) -> str:
    normalized = subcategory_key.replace(".", "_")
    return f"IND_{normalized}_{indicator_class}"


def build_indicator(
    *,
    domain: dict[str, Any],
    category: dict[str, Any],
    subcategory: dict[str, Any],
    indicator_class: str,
) -> dict[str, Any]:
    config = CLASS_CONFIG[indicator_class]
    indicator_key = build_indicator_key(
        subcategory["subcategory_key"],
        indicator_class,
    )

    source_keys = [
        source.upper()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        for source in subcategory["default_sources"]
    ]

    description = (
        f"{config['description_prefix']} for "
        f"{subcategory['name'].lower()} within the "
        f"{domain['name'].lower()} domain."
    )

    if indicator_class == "CONTRA":
        polarity = -1.0
    else:
        polarity = 1.0

    return {
        "indicator_key": indicator_key,
        "name": (
            f"{subcategory['name']} — "
            f"{config['name_suffix']}"
        ),
        "description": description,
        "taxonomy": {
            "domain_key": domain["domain_key"],
            "domain_name": domain["name"],
            "category_key": category["category_key"],
            "category_name": category["name"],
            "subcategory_key": subcategory[
                "subcategory_key"
            ],
            "subcategory_name": subcategory["name"],
        },
        "primary_domain": domain["name"],
        "secondary_domains": [],
        "default_class": indicator_class,
        "status": "ACTIVE",
        "measurement_unit": None,
        "measurement_type": config["measurement_type"],
        "expected_direction": config["expected_direction"],
        "polarity": polarity,
        "geographic_scope": {
            "levels": subcategory["geographic_levels"],
            "regions": [],
            "countries": [],
            "subnational_areas": [],
            "sites": [],
        },
        "sector_scope": [],
        "collection": {
            "method": subcategory[
                "default_collection_method"
            ],
            "source_keys": source_keys,
            "source_names": subcategory["default_sources"],
            "refresh_interval_minutes": subcategory[
                "default_refresh_interval_minutes"
            ],
            "stale_after_minutes": subcategory[
                "default_stale_after_minutes"
            ],
            "collection_priority": config[
                "collection_priority"
            ],
            "minimum_corroboration": (
                2 if indicator_class == "TRIGGER" else 1
            ),
            "dark_feed_detection": True,
        },
        "scoring": {
            "default_source_reliability": subcategory[
                "default_source_reliability"
            ],
            "default_relevance": config[
                "default_relevance"
            ],
            "default_weight": config["default_weight"],
            "normalization_method": "MIN_MAX_OR_RULE_BASED",
            "probability_model": "sews-logit-v1",
            "confidence_model": "sews-confidence-v1",
        },
        "thresholds": {
            "activation_threshold": (
                0.50 if indicator_class != "TRIGGER" else 1.0
            ),
            "critical_threshold": (
                0.80 if indicator_class != "TRIGGER" else 1.0
            ),
            "minimum_reliability": 40,
            "minimum_relevance": 40,
        },
        "ownership": {
            "owner_agent": subcategory["owner_agents"][0],
            "supporting_agents": subcategory[
                "owner_agents"
            ][1:],
        },
        "governance": {
            "analyst_review_required": (
                indicator_class == "TRIGGER"
            ),
            "immutable_observations": True,
            "contrary_evidence": (
                indicator_class == "CONTRA"
            ),
            "version": 1,
            "active": True,
        },
        "tags": list(
            dict.fromkeys(
                [
                    *subcategory["tags"],
                    indicator_class.lower(),
                    domain["domain_key"].lower(),
                ]
            )
        ),
    }


def validate_library(
    library: dict[str, Any],
    expected_subcategories: int,
) -> None:
    indicators = library["indicators"]
    expected_indicators = (
        expected_subcategories * len(INDICATOR_CLASSES)
    )

    if len(indicators) != expected_indicators:
        raise ValueError(
            "Indicator count mismatch: "
            f"expected {expected_indicators}, "
            f"found {len(indicators)}"
        )

    keys = [
        indicator["indicator_key"]
        for indicator in indicators
    ]

    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate indicator keys detected")

    class_counts = {
        indicator_class: 0
        for indicator_class in INDICATOR_CLASSES
    }

    subcategory_classes: dict[str, set[str]] = {}

    for indicator in indicators:
        indicator_class = indicator["default_class"]
        class_counts[indicator_class] += 1

        subcategory_key = indicator["taxonomy"][
            "subcategory_key"
        ]

        subcategory_classes.setdefault(
            subcategory_key,
            set(),
        ).add(indicator_class)

        if indicator["scoring"]["default_weight"] < 0:
            raise ValueError(
                f"Negative weight: "
                f"{indicator['indicator_key']}"
            )

        refresh = indicator["collection"][
            "refresh_interval_minutes"
        ]
        stale = indicator["collection"][
            "stale_after_minutes"
        ]

        if stale < refresh:
            raise ValueError(
                f"Invalid freshness configuration: "
                f"{indicator['indicator_key']}"
            )

    required_classes = set(INDICATOR_CLASSES)

    for subcategory_key, classes in (
        subcategory_classes.items()
    ):
        if classes != required_classes:
            raise ValueError(
                f"Incomplete class coverage for "
                f"{subcategory_key}: {sorted(classes)}"
            )

    for indicator_class, count in class_counts.items():
        if count != expected_subcategories:
            raise ValueError(
                f"{indicator_class} count mismatch: "
                f"{count}"
            )


def main() -> None:
    if not TAXONOMY_PATH.exists():
        raise SystemExit(
            f"Missing taxonomy: {TAXONOMY_PATH}"
        )

    taxonomy = json.loads(TAXONOMY_PATH.read_text())

    indicators: list[dict[str, Any]] = []

    for domain in taxonomy["domains"]:
        for category in domain["categories"]:
            for subcategory in category["subcategories"]:
                for indicator_class in INDICATOR_CLASSES:
                    indicators.append(
                        build_indicator(
                            domain=domain,
                            category=category,
                            subcategory=subcategory,
                            indicator_class=indicator_class,
                        )
                    )

    library = {
        "library_name": (
            "Sovereign Intelligence Global Indicator Library"
        ),
        "library_version": "sews-indicator-library-v1",
        "taxonomy_version": taxonomy[
            "taxonomy_version"
        ],
        "schema_version": 1,
        "domain_count": taxonomy["domain_count"],
        "category_count": taxonomy["category_count"],
        "subcategory_count": taxonomy[
            "subcategory_count"
        ],
        "indicator_count": len(indicators),
        "indicator_classes": list(INDICATOR_CLASSES),
        "generation_strategy": (
            "One PRECURSOR, ACCELERANT, TRIGGER, and "
            "CONTRA definition per taxonomy subcategory"
        ),
        "indicators": indicators,
    }

    validate_library(
        library,
        expected_subcategories=taxonomy[
            "subcategory_count"
        ],
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            library,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    print(f"✅ Created {OUTPUT_PATH}")
    print(
        f"✅ Indicators: "
        f"{library['indicator_count']:,}"
    )
    print(
        f"✅ Subcategories: "
        f"{library['subcategory_count']}"
    )

    for indicator_class in INDICATOR_CLASSES:
        count = sum(
            1
            for indicator in indicators
            if indicator["default_class"]
            == indicator_class
        )
        print(f"✅ {indicator_class}: {count}")


if __name__ == "__main__":
    main()
