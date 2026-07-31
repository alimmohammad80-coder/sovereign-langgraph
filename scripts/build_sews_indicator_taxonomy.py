from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUTPUT_PATH = Path("app/data/sews_global_indicator_taxonomy.json")


DOMAIN_CONFIG: list[dict[str, Any]] = [
    {
        "domain_key": "CONFLICT_MILITARY",
        "name": "Conflict and Military",
        "description": (
            "Military posture, force readiness, armed conflict, escalation, "
            "deterrence, deployments, logistics, and kinetic activity."
        ),
        "owner_agents": [
            "conflict_monitoring",
            "executive_briefing",
        ],
        "default_sources": [
            "Government defense releases",
            "GDELT",
            "Google News RSS",
            "ReliefWeb",
            "ACLED",
            "UN reporting",
        ],
        "categories": {
            "FORCE_POSTURE": [
                "Ground force deployment",
                "Naval deployment",
                "Air force deployment",
                "Missile force posture",
                "Reserve mobilization",
                "Forward basing",
            ],
            "MILITARY_ACTIVITY": [
                "Military exercises",
                "Air sorties",
                "Naval patrols",
                "Border activity",
                "Weapons testing",
                "Readiness drills",
            ],
            "LOGISTICS_SUSTAINMENT": [
                "Fuel movement",
                "Ammunition movement",
                "Rail logistics",
                "Military airlift",
                "Sealift capacity",
                "Field medical preparation",
            ],
            "COMMAND_CONTROL": [
                "Command changes",
                "Communications activity",
                "Electronic warfare",
                "Command post activation",
                "Strategic signaling",
                "Rules of engagement changes",
            ],
            "KINETIC_EVENTS": [
                "Armed clashes",
                "Missile launches",
                "Airstrikes",
                "Artillery activity",
                "Maritime interdictions",
                "Infrastructure attacks",
            ],
            "ESCALATION_DEESCALATION": [
                "Escalatory rhetoric",
                "Force concentration",
                "Ceasefire activity",
                "Deconfliction contacts",
                "Military withdrawals",
                "Confidence-building measures",
            ],
            "WEAPONS_PROLIFERATION": [
                "Nuclear activity",
                "Ballistic missile development",
                "Drone proliferation",
                "Chemical weapons indicators",
                "Arms transfers",
                "Dual-use technology acquisition",
            ],
        },
    },
    {
        "domain_key": "POLITICAL_STABILITY",
        "name": "Political Stability",
        "description": (
            "Government durability, institutional cohesion, elite competition, "
            "public legitimacy, political transition, and civil disorder."
        ),
        "owner_agents": [
            "political_stability",
            "executive_briefing",
        ],
        "default_sources": [
            "Government releases",
            "Election authorities",
            "World Bank",
            "GDELT",
            "ACLED",
            "UN reporting",
        ],
        "categories": {
            "GOVERNMENT_STABILITY": [
                "Cabinet resignations",
                "Coalition breakdown",
                "Leadership succession",
                "Government approval",
                "No-confidence activity",
                "Executive authority erosion",
            ],
            "ELITE_COHESION": [
                "Elite fragmentation",
                "Party defections",
                "Military political intervention",
                "Business elite opposition",
                "Regional elite resistance",
                "Security-service loyalty",
            ],
            "ELECTIONS_LEGITIMACY": [
                "Election administration",
                "Electoral violence",
                "Fraud allegations",
                "Opposition participation",
                "Turnout anomalies",
                "Recognition of results",
            ],
            "CIVIL_UNREST": [
                "Protest volume",
                "Protest intensity",
                "Strike activity",
                "Riot activity",
                "Police response",
                "Emergency restrictions",
            ],
            "INSTITUTIONAL_STRESS": [
                "Constitutional disputes",
                "Judicial confrontation",
                "Legislative paralysis",
                "Emergency powers",
                "Institutional purges",
                "Public administration disruption",
            ],
            "REGIME_TRANSITION": [
                "Coup indicators",
                "Succession planning",
                "Interim government formation",
                "Power-sharing negotiations",
                "Regime collapse indicators",
                "Exile leadership activity",
            ],
        },
    },
    {
        "domain_key": "ECONOMIC_FINANCIAL",
        "name": "Economic and Financial",
        "description": (
            "Macroeconomic resilience, sovereign risk, banking stress, monetary "
            "conditions, fiscal capacity, markets, trade, and capital flows."
        ),
        "owner_agents": [
            "economic_risk",
            "financial_risk",
            "executive_briefing",
        ],
        "default_sources": [
            "IMF",
            "World Bank",
            "FRED",
            "OECD",
            "Central banks",
            "National statistics agencies",
        ],
        "categories": {
            "MACROECONOMIC_PERFORMANCE": [
                "GDP growth",
                "Industrial production",
                "Retail activity",
                "Employment",
                "Productivity",
                "Business confidence",
            ],
            "INFLATION_PRICES": [
                "Consumer inflation",
                "Producer inflation",
                "Food inflation",
                "Energy inflation",
                "Housing inflation",
                "Inflation expectations",
            ],
            "MONETARY_FINANCIAL_CONDITIONS": [
                "Policy rates",
                "Real interest rates",
                "Credit growth",
                "Liquidity conditions",
                "Money supply",
                "Yield curve stress",
            ],
            "SOVEREIGN_RISK": [
                "Bond spreads",
                "Sovereign CDS",
                "Debt-service burden",
                "External debt",
                "Default probability",
                "Debt restructuring activity",
            ],
            "BANKING_SYSTEM": [
                "Deposit flight",
                "Nonperforming loans",
                "Bank liquidity",
                "Bank solvency",
                "Credit contraction",
                "Emergency central-bank support",
            ],
            "CURRENCY_EXTERNAL_BALANCE": [
                "Exchange-rate pressure",
                "Foreign reserves",
                "Current account",
                "Capital outflows",
                "Parallel exchange rates",
                "Import coverage",
            ],
            "FISCAL_STRESS": [
                "Budget deficit",
                "Revenue shortfall",
                "Subsidy burden",
                "Public wage pressure",
                "Fiscal arrears",
                "Emergency financing",
            ],
        },
    },
    {
        "domain_key": "ENERGY_SUPPLY_CHAIN",
        "name": "Energy and Supply Chain",
        "description": (
            "Energy security, maritime trade, logistics, commodities, industrial "
            "dependencies, ports, corridors, chokepoints, and supply disruption."
        ),
        "owner_agents": [
            "energy_security",
            "supply_chain",
            "trade_sanctions",
            "executive_briefing",
        ],
        "default_sources": [
            "EIA",
            "UN Comtrade",
            "Port authorities",
            "AIS maritime data",
            "Commodity markets",
            "World Bank",
        ],
        "categories": {
            "OIL_MARKETS": [
                "Crude production",
                "Crude exports",
                "Refinery utilization",
                "Oil inventories",
                "Tanker rates",
                "Oil price volatility",
            ],
            "NATURAL_GAS_LNG": [
                "Gas production",
                "Pipeline flows",
                "LNG exports",
                "LNG vessel movement",
                "Gas storage",
                "Gas price volatility",
            ],
            "POWER_ELECTRICITY": [
                "Generation capacity",
                "Grid reliability",
                "Electricity demand",
                "Power outages",
                "Fuel availability",
                "Cross-border electricity flows",
            ],
            "PORTS_MARITIME": [
                "Port throughput",
                "Port congestion",
                "Vessel waiting time",
                "Container dwell time",
                "Port closure",
                "Labor disruption",
            ],
            "CHOKEPOINTS_CORRIDORS": [
                "Chokepoint transit volume",
                "Shipping rerouting",
                "Canal restrictions",
                "Maritime security incidents",
                "Insurance premiums",
                "Transit delay",
            ],
            "FREIGHT_LOGISTICS": [
                "Container freight rates",
                "Bulk shipping rates",
                "Air cargo volume",
                "Rail freight",
                "Trucking capacity",
                "Warehouse utilization",
            ],
            "CRITICAL_COMMODITIES": [
                "Critical minerals production",
                "Export restrictions",
                "Commodity inventories",
                "Processing concentration",
                "Industrial input shortages",
                "Commodity price shock",
            ],
        },
    },
    {
        "domain_key": "CYBER_INFORMATION",
        "name": "Cyber and Information Operations",
        "description": (
            "Cyber threats, critical-infrastructure compromise, influence "
            "operations, disinformation, digital repression, and network disruption."
        ),
        "owner_agents": [
            "cyber_information_operations",
            "executive_briefing",
        ],
        "default_sources": [
            "CISA",
            "National CERTs",
            "Cybersecurity vendors",
            "Government advisories",
            "GDELT",
            "Open-source reporting",
        ],
        "categories": {
            "CYBER_INTRUSION": [
                "Malware activity",
                "Credential compromise",
                "Network intrusion",
                "Zero-day exploitation",
                "Supply-chain compromise",
                "Persistent access indicators",
            ],
            "CRITICAL_INFRASTRUCTURE_CYBER": [
                "Energy-sector attacks",
                "Telecommunications attacks",
                "Financial-sector attacks",
                "Transport-system attacks",
                "Water-system attacks",
                "Government-network attacks",
            ],
            "CYBER_DISRUPTION": [
                "Ransomware incidents",
                "DDoS activity",
                "Service outages",
                "Data destruction",
                "Cloud disruption",
                "Internet routing anomalies",
            ],
            "INFORMATION_OPERATIONS": [
                "Coordinated influence activity",
                "Synthetic media",
                "Narrative amplification",
                "Bot-network activity",
                "State-media coordination",
                "Cross-platform manipulation",
            ],
            "ELECTION_INFORMATION_RISK": [
                "Election disinformation",
                "Voter suppression narratives",
                "Election-system intrusion",
                "Candidate impersonation",
                "Foreign influence activity",
                "Result-denial mobilization",
            ],
            "DIGITAL_REPRESSION": [
                "Internet shutdown",
                "Platform blocking",
                "Surveillance expansion",
                "Online censorship",
                "Journalist targeting",
                "Digital identity restrictions",
            ],
        },
    },
    {
        "domain_key": "HUMANITARIAN_HEALTH",
        "name": "Humanitarian and Public Health",
        "description": (
            "Population displacement, food insecurity, health emergencies, "
            "humanitarian access, disease transmission, and essential services."
        ),
        "owner_agents": [
            "humanitarian_monitoring",
            "political_stability",
            "executive_briefing",
        ],
        "default_sources": [
            "WHO",
            "ReliefWeb",
            "WFP",
            "FAO",
            "UNHCR",
            "UN OCHA",
        ],
        "categories": {
            "POPULATION_DISPLACEMENT": [
                "Refugee outflows",
                "Internal displacement",
                "Border crossings",
                "Return movements",
                "Camp population",
                "Forced relocation",
            ],
            "FOOD_SECURITY": [
                "Food-price stress",
                "Acute food insecurity",
                "Crop production",
                "Import dependency",
                "Malnutrition",
                "Food assistance coverage",
            ],
            "PUBLIC_HEALTH": [
                "Disease incidence",
                "Mortality anomalies",
                "Hospital capacity",
                "Vaccination coverage",
                "Medical supply availability",
                "Cross-border transmission",
            ],
            "HUMANITARIAN_ACCESS": [
                "Aid access constraints",
                "Convoy obstruction",
                "Humanitarian worker incidents",
                "Border closure",
                "Funding shortfall",
                "Aid-delivery volume",
            ],
            "ESSENTIAL_SERVICES": [
                "Water access",
                "Sanitation access",
                "Healthcare access",
                "Electricity access",
                "Shelter availability",
                "Communications access",
            ],
            "PROTECTION_RISK": [
                "Civilian casualties",
                "Gender-based violence",
                "Child protection incidents",
                "Detention activity",
                "Forced recruitment",
                "Civilian-targeting patterns",
            ],
        },
    },
    {
        "domain_key": "CLIMATE_ENVIRONMENT",
        "name": "Climate and Environmental Risk",
        "description": (
            "Climate hazards, water stress, environmental degradation, natural "
            "disasters, agricultural exposure, and climate-linked instability."
        ),
        "owner_agents": [
            "environmental_risk",
            "economic_risk",
            "executive_briefing",
        ],
        "default_sources": [
            "NOAA",
            "NASA",
            "Copernicus",
            "FAO",
            "World Bank",
            "National meteorological agencies",
        ],
        "categories": {
            "EXTREME_WEATHER": [
                "Extreme heat",
                "Extreme cold",
                "Severe storms",
                "Cyclone activity",
                "Heavy precipitation",
                "Weather-related disruption",
            ],
            "DROUGHT_WATER_STRESS": [
                "Drought severity",
                "Reservoir levels",
                "Groundwater depletion",
                "River flow",
                "Urban water restrictions",
                "Agricultural water stress",
            ],
            "FLOOD_COASTAL_RISK": [
                "River flooding",
                "Flash flooding",
                "Coastal flooding",
                "Storm surge",
                "Sea-level anomaly",
                "Flood-related displacement",
            ],
            "WILDFIRE_LAND_DEGRADATION": [
                "Wildfire activity",
                "Vegetation stress",
                "Soil degradation",
                "Desertification",
                "Deforestation",
                "Air-quality degradation",
            ],
            "AGRICULTURAL_CLIMATE": [
                "Crop yield anomaly",
                "Planting disruption",
                "Harvest disruption",
                "Livestock stress",
                "Pest outbreaks",
                "Agricultural input stress",
            ],
            "NATURAL_DISASTER": [
                "Earthquake activity",
                "Volcanic activity",
                "Landslide risk",
                "Tsunami risk",
                "Infrastructure exposure",
                "Disaster-response capacity",
            ],
        },
    },
    {
        "domain_key": "CORPORATE_STRATEGIC",
        "name": "Corporate and Strategic Exposure",
        "description": (
            "Corporate resilience, sanctions exposure, ownership, operational "
            "dependency, strategic industries, investment risk, and business continuity."
        ),
        "owner_agents": [
            "corporate_exposure",
            "trade_sanctions",
            "financial_risk",
            "executive_briefing",
        ],
        "default_sources": [
            "OFAC",
            "Company filings",
            "UN Comtrade",
            "World Bank",
            "Market data",
            "Government trade authorities",
        ],
        "categories": {
            "SANCTIONS_EXPORT_CONTROLS": [
                "Sanctions designation",
                "Export-control expansion",
                "License restriction",
                "Secondary-sanctions exposure",
                "Entity-list exposure",
                "Compliance enforcement",
            ],
            "CORPORATE_FINANCIAL_STRESS": [
                "Credit downgrade",
                "Liquidity stress",
                "Earnings deterioration",
                "Debt maturity risk",
                "Equity volatility",
                "Default indicators",
            ],
            "OPERATIONAL_DEPENDENCY": [
                "Single-source dependency",
                "Country concentration",
                "Supplier concentration",
                "Logistics dependency",
                "Energy dependency",
                "Technology dependency",
            ],
            "OWNERSHIP_GOVERNANCE": [
                "State ownership",
                "Beneficial ownership risk",
                "Board instability",
                "Government intervention",
                "Corruption exposure",
                "Governance controversy",
            ],
            "STRATEGIC_INDUSTRIES": [
                "Semiconductor exposure",
                "Defense-industrial exposure",
                "Telecommunications exposure",
                "Critical-minerals exposure",
                "Pharmaceutical exposure",
                "Energy-sector exposure",
            ],
            "BUSINESS_CONTINUITY": [
                "Facility closure",
                "Workforce disruption",
                "Insurance availability",
                "Cyber continuity",
                "Supplier substitution capacity",
                "Recovery time",
            ],
        },
    },
]


DEFAULT_COLLECTION_METHODS = {
    "CONFLICT_MILITARY": "WEB_COLLECTION",
    "POLITICAL_STABILITY": "WEB_COLLECTION",
    "ECONOMIC_FINANCIAL": "API",
    "ENERGY_SUPPLY_CHAIN": "API",
    "CYBER_INFORMATION": "WEB_COLLECTION",
    "HUMANITARIAN_HEALTH": "API",
    "CLIMATE_ENVIRONMENT": "API",
    "CORPORATE_STRATEGIC": "DATABASE",
}


DEFAULT_REFRESH_MINUTES = {
    "CONFLICT_MILITARY": 180,
    "POLITICAL_STABILITY": 360,
    "ECONOMIC_FINANCIAL": 1440,
    "ENERGY_SUPPLY_CHAIN": 360,
    "CYBER_INFORMATION": 180,
    "HUMANITARIAN_HEALTH": 720,
    "CLIMATE_ENVIRONMENT": 360,
    "CORPORATE_STRATEGIC": 1440,
}


def slugify(value: str) -> str:
    cleaned = []
    for character in value.upper():
        cleaned.append(character if character.isalnum() else "_")

    slug = "".join(cleaned)

    while "__" in slug:
        slug = slug.replace("__", "_")

    return slug.strip("_")


def build_taxonomy() -> dict[str, Any]:
    domains: list[dict[str, Any]] = []
    category_count = 0
    subcategory_count = 0

    for domain_position, domain in enumerate(DOMAIN_CONFIG, start=1):
        categories: list[dict[str, Any]] = []

        for category_position, (
            category_key,
            subcategory_names,
        ) in enumerate(domain["categories"].items(), start=1):
            category_count += 1

            subcategories: list[dict[str, Any]] = []

            for subcategory_position, name in enumerate(
                subcategory_names,
                start=1,
            ):
                subcategory_count += 1

                subcategory_key = (
                    f"{domain['domain_key']}.{category_key}."
                    f"{slugify(name)}"
                )

                subcategories.append(
                    {
                        "subcategory_key": subcategory_key,
                        "name": name,
                        "description": (
                            f"Standardized intelligence indicator family for "
                            f"{name.lower()}."
                        ),
                        "default_indicator_class": "PRECURSOR",
                        "supported_indicator_classes": [
                            "PRECURSOR",
                            "ACCELERANT",
                            "TRIGGER",
                            "CONTRA",
                        ],
                        "default_collection_method": (
                            DEFAULT_COLLECTION_METHODS[
                                domain["domain_key"]
                            ]
                        ),
                        "default_refresh_interval_minutes": (
                            DEFAULT_REFRESH_MINUTES[
                                domain["domain_key"]
                            ]
                        ),
                        "default_stale_after_minutes": (
                            DEFAULT_REFRESH_MINUTES[
                                domain["domain_key"]
                            ]
                            * 3
                        ),
                        "default_source_reliability": 75,
                        "default_relevance": 75,
                        "default_weight": 1.0,
                        "measurement_templates": [
                            "EVENT_COUNT",
                            "INDEX",
                            "NUMERIC",
                            "BOOLEAN",
                            "PROBABILITY",
                        ],
                        "geographic_levels": [
                            "GLOBAL",
                            "REGIONAL",
                            "COUNTRY",
                            "SUBNATIONAL",
                            "SITE",
                        ],
                        "owner_agents": domain["owner_agents"],
                        "default_sources": domain["default_sources"],
                        "tags": [
                            domain["domain_key"].lower(),
                            category_key.lower(),
                            slugify(name).lower(),
                        ],
                        "position": subcategory_position,
                        "active": True,
                    }
                )

            category_taxonomy_key = (
                f"{domain['domain_key']}.{category_key}"
            )

            categories.append(
                {
                    "category_key": category_taxonomy_key,
                    "name": category_key.replace("_", " ").title(),
                    "description": (
                        f"Indicator category covering "
                        f"{category_key.replace('_', ' ').lower()}."
                    ),
                    "subcategory_count": len(subcategories),
                    "subcategories": subcategories,
                    "position": category_position,
                    "active": True,
                }
            )

        domains.append(
            {
                "domain_key": domain["domain_key"],
                "name": domain["name"],
                "description": domain["description"],
                "owner_agents": domain["owner_agents"],
                "default_sources": domain["default_sources"],
                "category_count": len(categories),
                "categories": categories,
                "position": domain_position,
                "active": True,
            }
        )

    return {
        "taxonomy_name": (
            "Sovereign Intelligence Global Indicator Taxonomy"
        ),
        "taxonomy_version": "sews-indicator-taxonomy-v1",
        "schema_version": 1,
        "domain_count": len(domains),
        "category_count": category_count,
        "subcategory_count": subcategory_count,
        "indicator_capacity_target": 10000,
        "supported_indicator_classes": [
            "PRECURSOR",
            "ACCELERANT",
            "TRIGGER",
            "CONTRA",
        ],
        "domains": domains,
    }


def validate_taxonomy(taxonomy: dict[str, Any]) -> None:
    domain_keys: set[str] = set()
    category_keys: set[str] = set()
    subcategory_keys: set[str] = set()

    for domain in taxonomy["domains"]:
        domain_key = domain["domain_key"]

        if domain_key in domain_keys:
            raise ValueError(f"Duplicate domain key: {domain_key}")

        domain_keys.add(domain_key)

        for category in domain["categories"]:
            category_key = category["category_key"]

            if category_key in category_keys:
                raise ValueError(
                    f"Duplicate category key: {category_key}"
                )

            category_keys.add(category_key)

            for subcategory in category["subcategories"]:
                subcategory_key = subcategory["subcategory_key"]

                if subcategory_key in subcategory_keys:
                    raise ValueError(
                        f"Duplicate subcategory key: {subcategory_key}"
                    )

                subcategory_keys.add(subcategory_key)

                if "CONTRA" not in subcategory[
                    "supported_indicator_classes"
                ]:
                    raise ValueError(
                        f"CONTRA unsupported: {subcategory_key}"
                    )

    if len(domain_keys) != taxonomy["domain_count"]:
        raise ValueError("Domain count mismatch")

    if len(category_keys) != taxonomy["category_count"]:
        raise ValueError("Category count mismatch")

    if len(subcategory_keys) != taxonomy["subcategory_count"]:
        raise ValueError("Subcategory count mismatch")


def main() -> None:
    taxonomy = build_taxonomy()
    validate_taxonomy(taxonomy)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            taxonomy,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    print(f"✅ Created {OUTPUT_PATH}")
    print(f"✅ Domains: {taxonomy['domain_count']}")
    print(f"✅ Categories: {taxonomy['category_count']}")
    print(f"✅ Subcategories: {taxonomy['subcategory_count']}")
    print(
        "✅ Indicator capacity target: "
        f"{taxonomy['indicator_capacity_target']:,}"
    )


if __name__ == "__main__":
    main()
