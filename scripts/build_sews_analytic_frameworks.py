from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WARNING_REGISTRY_PATH = ROOT / "app/data/sews_global_warning_registry.json"
TAXONOMY_PATH = ROOT / "app/data/sews_global_indicator_taxonomy.json"
INDICATOR_LIBRARY_PATH = ROOT / "app/data/sews_global_indicator_library.json"
OUTPUT_PATH = ROOT / "app/data/sews_global_analytic_frameworks.json"

INDICATOR_CLASSES = ("PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA")

FRAMEWORKS: dict[str, list[tuple[str, str, list[tuple[str, list[str]]]]]] = {
    "Conflict and Military": [
        ("Force Posture and Readiness", "Are relevant forces increasing readiness, deployment posture, or operational capacity?", [
            ("Force Deployments", ["deployment", "mobilization", "troop", "force posture"]),
            ("Readiness and Exercises", ["readiness", "exercise", "training", "alert"]),
            ("Logistics and Sustainment", ["logistics", "stockpile", "ammunition", "sustainment"]),
        ]),
        ("Escalation and Hostile Intent", "Is evidence of hostile intent, coercion, or preparation for escalation increasing?", [
            ("Threats and Signaling", ["threat", "rhetoric", "warning", "coercion"]),
            ("Operational Preparation", ["authorization", "command", "targeting", "preparation"]),
            ("Trigger Events", ["attack", "strike", "incursion", "casualty"]),
        ]),
    ],
    "Political Stability": [
        ("Government Stability and Control", "Is the government losing authority, administrative control, or elite support?", [
            ("Elite Cohesion", ["elite", "faction", "defection", "coalition"]),
            ("Institutional Control", ["government", "institution", "state capacity", "administration"]),
            ("Security Apparatus Loyalty", ["security forces", "loyalty", "police", "military support"]),
        ]),
        ("Public Mobilization and Unrest", "Are grievances translating into organized unrest or sustained political mobilization?", [
            ("Protest Activity", ["protest", "demonstration", "unrest", "civil disorder"]),
            ("Grievance Intensity", ["grievance", "sentiment", "dissatisfaction", "anger"]),
            ("Opposition Coordination", ["opposition", "coordination", "movement", "organizing"]),
        ]),
    ],
    "Economic and Financial": [
        ("Macroeconomic Stress", "Are inflation, growth, employment, or fiscal conditions moving toward systemic stress?", [
            ("Growth and Output", ["growth", "gdp", "output", "recession"]),
            ("Inflation and Purchasing Power", ["inflation", "price", "purchasing power"]),
            ("Fiscal Stability", ["fiscal", "budget", "deficit", "revenue"]),
        ]),
        ("Financial-System Stability", "Are banking, liquidity, credit, currency, or capital-market conditions deteriorating?", [
            ("Banking Stress", ["bank", "liquidity", "deposit", "nonperforming"]),
            ("Currency and Capital Flows", ["currency", "exchange rate", "capital flow", "reserve"]),
            ("Credit and Market Stress", ["credit", "bond", "yield", "default"]),
        ]),
    ],
    "Energy and Supply Chain": [
        ("Physical Supply Disruption", "Are infrastructure, transport routes, production sites, or inventories at risk?", [
            ("Infrastructure Availability", ["infrastructure", "pipeline", "terminal", "refinery"]),
            ("Transport and Routing", ["shipping", "route", "chokepoint", "port", "transit"]),
            ("Inventory and Capacity", ["inventory", "capacity", "storage", "production"]),
        ]),
        ("Commercial and Market Response", "Are markets, insurers, carriers, or suppliers confirming worsening disruption risk?", [
            ("Commodity Prices", ["commodity", "oil price", "gas price", "spot price"]),
            ("Freight and Insurance", ["freight", "insurance", "premium", "shipping cost"]),
            ("Supplier Behavior", ["supplier", "rerouting", "cancellation", "delivery"]),
        ]),
    ],
    "Cyber and Information Operations": [
        ("Cyber Threat Activity", "Are hostile actors increasing reconnaissance, access, persistence, or disruption?", [
            ("Reconnaissance and Access", ["reconnaissance", "scanning", "access", "credential"]),
            ("Malware and Exploitation", ["malware", "exploit", "vulnerability", "ransomware"]),
            ("Operational Disruption", ["outage", "denial of service", "destructive", "disruption"]),
        ]),
        ("Information Manipulation", "Are coordinated influence or deception operations changing the information environment?", [
            ("Narrative Propagation", ["narrative", "propaganda", "misinformation", "disinformation"]),
            ("Coordinated Amplification", ["bot", "amplification", "inauthentic", "coordinated"]),
            ("Audience Impact", ["public opinion", "sentiment", "polarization", "trust"]),
        ]),
    ],
    "Humanitarian and Public Health": [
        ("Population Impact", "Are mortality, morbidity, displacement, or deprivation increasing materially?", [
            ("Mortality and Morbidity", ["mortality", "morbidity", "death", "disease"]),
            ("Displacement", ["displacement", "refugee", "migration", "evacuation"]),
            ("Basic Needs", ["food", "water", "shelter", "deprivation"]),
        ]),
        ("Response-System Capacity", "Can health, humanitarian, and governmental systems absorb emerging demand?", [
            ("Healthcare Capacity", ["hospital", "healthcare", "medical supply", "health worker"]),
            ("Humanitarian Access", ["humanitarian access", "aid delivery", "relief"]),
            ("Government Response", ["government response", "emergency response", "public health"]),
        ]),
    ],
    "Climate and Environmental Risk": [
        ("Hazard Development", "Are environmental hazards increasing in probability, intensity, duration, or reach?", [
            ("Hazard Probability", ["hazard", "forecast", "weather", "climate anomaly"]),
            ("Hazard Intensity", ["intensity", "severity", "magnitude", "extreme"]),
            ("Duration and Spread", ["duration", "spread", "affected area", "persistence"]),
        ]),
        ("Exposure and Vulnerability", "Are populations, infrastructure, agriculture, or assets becoming more exposed?", [
            ("Population Exposure", ["population exposure", "community", "urban"]),
            ("Infrastructure Exposure", ["infrastructure exposure", "asset risk", "utility"]),
            ("Agricultural Exposure", ["agriculture", "crop", "water resource", "land"]),
        ]),
    ],
    "Corporate and Strategic Exposure": [
        ("Direct Corporate Exposure", "Are operations, personnel, facilities, or revenue directly exposed?", [
            ("Operational Footprint", ["operation", "facility", "office", "site"]),
            ("Revenue and Market Exposure", ["revenue", "market exposure", "sales", "customer"]),
            ("Personnel Exposure", ["personnel", "employee", "workforce", "duty of care"]),
        ]),
        ("Dependency and Continuity Risk", "Are dependencies amplifying risk, and can the organization absorb disruption?", [
            ("Supplier Dependency", ["supplier", "vendor", "dependency", "single source"]),
            ("Technology and Financial Dependency", ["technology", "platform", "counterparty", "financing"]),
            ("Business Continuity", ["business continuity", "contingency", "recovery", "redundancy"]),
        ]),
    ],
}

DOMAIN_HINTS = {
    "Conflict and Military": ["conflict", "military", "war", "attack", "taiwan", "ukraine", "nato", "north korea", "blockade"],
    "Political Stability": ["political", "election", "government", "regime", "coup", "unrest", "afghanistan", "pakistan", "sahel"],
    "Economic and Financial": ["economic", "financial", "debt", "currency", "bank", "sovereign"],
    "Energy and Supply Chain": ["energy", "supply", "shipping", "hormuz", "suez", "red sea", "semiconductor", "minerals", "oil", "gas"],
    "Cyber and Information Operations": ["cyber", "information", "disinformation", "malware", "interference"],
    "Humanitarian and Public Health": ["humanitarian", "health", "disease", "food", "famine", "outbreak", "displacement"],
    "Climate and Environmental Risk": ["climate", "environment", "weather", "drought", "flood", "wildfire", "storm"],
    "Corporate and Strategic Exposure": ["corporate", "company", "business", "portfolio", "strategic exposure"],
}

def slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")

def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())

def warning_problems(registry: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("warning_problems", "problems", "items", "registry", "data"):
        if isinstance(registry.get(key), list):
            return registry[key]
    raise ValueError("Could not find the warning-problem list.")

def get_problem_key(problem: dict[str, Any], index: int) -> str:
    return str(problem.get("warning_problem_key") or problem.get("problem_key") or problem.get("key") or problem.get("id") or f"WP_{index+1:03d}")

def get_problem_name(problem: dict[str, Any]) -> str:
    return str(problem.get("name") or problem.get("title") or problem.get("warning_problem_name") or "Unnamed Warning Problem")

def choose_domains(problem: dict[str, Any]) -> list[str]:
    explicit = problem.get("primary_domain") or problem.get("domain")
    if isinstance(explicit, str) and explicit in FRAMEWORKS:
        return [explicit]
    text = json.dumps(problem, ensure_ascii=False).lower()
    scores = Counter({domain: sum(hint in text for hint in hints) for domain, hints in DOMAIN_HINTS.items()})
    selected = [domain for domain, score in scores.most_common(2) if score > 0]
    return selected or ["Political Stability"]

def flatten_taxonomy(taxonomy: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for domain in taxonomy["domains"]:
        for category in domain["categories"]:
            for subcategory in category["subcategories"]:
                rows.append({
                    "domain": domain["name"],
                    "subcategory_key": subcategory["subcategory_key"],
                    "text": " ".join([subcategory.get("name", ""), subcategory.get("description", ""), category.get("name", ""), " ".join(subcategory.get("tags", []))]).lower(),
                })
    return rows

def select_subcategories(domain: str, keywords: list[str], rows: list[dict[str, str]], limit: int = 4) -> list[str]:
    candidates = [row for row in rows if row["domain"] == domain]
    ranked = sorted(candidates, key=lambda row: (-sum(3 for keyword in keywords if keyword in row["text"]), row["subcategory_key"]))
    return [row["subcategory_key"] for row in ranked[:limit]]

def main() -> None:
    registry = load(WARNING_REGISTRY_PATH)
    taxonomy = load(TAXONOMY_PATH)
    library = load(INDICATOR_LIBRARY_PATH)
    problems = warning_problems(registry)
    taxonomy_rows = flatten_taxonomy(taxonomy)
    indicator_index = {(item["taxonomy"]["subcategory_key"], item["default_class"]): item["indicator_key"] for item in library["indicators"]}
    output_problems = []

    for problem_index, problem in enumerate(problems):
        problem_key = get_problem_key(problem, problem_index)
        problem_name = get_problem_name(problem)
        domains = choose_domains(problem)
        built_frameworks = []
        for domain in domains:
            templates = FRAMEWORKS[domain]
            for framework_index, (framework_name, question, groups) in enumerate(templates, 1):
                built_groups = []
                for group_index, (group_name, keywords) in enumerate(groups, 1):
                    selected = select_subcategories(domain, keywords, taxonomy_rows)
                    mappings = []
                    for subcategory_key in selected:
                        for indicator_class in INDICATOR_CLASSES:
                            indicator_key = indicator_index.get((subcategory_key, indicator_class))
                            if indicator_key:
                                mappings.append({"indicator_key": indicator_key, "indicator_class": indicator_class, "subcategory_key": subcategory_key})
                    built_groups.append({
                        "indicator_group_key": f"IG_{slug(problem_key)}_{slug(domain)}_{framework_index:02d}_{group_index:02d}",
                        "name": group_name,
                        "analytic_purpose": f"Assess {group_name.lower()} for {problem_name}.",
                        "domain": domain,
                        "weight": round(1 / len(groups), 4),
                        "aggregation_method": "WEIGHTED_EVIDENCE_BALANCE",
                        "minimum_active_indicators": 2,
                        "minimum_corroborated_sources": 1,
                        "subcategory_keys": selected,
                        "mapped_indicators": mappings,
                    })
                built_frameworks.append({
                    "analytic_framework_key": f"AF_{slug(problem_key)}_{slug(domain)}_{framework_index:02d}",
                    "name": framework_name,
                    "analytic_question": question,
                    "warning_problem_key": problem_key,
                    "warning_problem_name": problem_name,
                    "domain": domain,
                    "weight": round(1 / (len(domains) * len(templates)), 4),
                    "status": "ACTIVE",
                    "aggregation_method": "WEIGHTED_GROUP_LOGIT",
                    "indicator_groups": built_groups,
                })
        output_problems.append({"warning_problem_key": problem_key, "warning_problem_name": problem_name, "assigned_domains": domains, "framework_count": len(built_frameworks), "frameworks": built_frameworks})

    frameworks = [f for p in output_problems for f in p["frameworks"]]
    groups = [g for f in frameworks for g in f["indicator_groups"]]
    for group in groups:
        classes = {item["indicator_class"] for item in group["mapped_indicators"]}
        if classes != set(INDICATOR_CLASSES):
            raise ValueError(f"Incomplete class coverage in {group['indicator_group_key']}: {sorted(classes)}")

    output = {
        "registry_name": "Sovereign Intelligence Analytic Framework Registry",
        "registry_version": "sews-analytic-framework-registry-v1",
        "schema_version": 1,
        "taxonomy_version": taxonomy["taxonomy_version"],
        "indicator_library_version": library["library_version"],
        "warning_problem_count": len(output_problems),
        "analytic_framework_count": len(frameworks),
        "indicator_group_count": len(groups),
        "mapped_indicator_reference_count": sum(len(g["mapped_indicators"]) for g in groups),
        "warning_problems": output_problems,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"✅ Created {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"✅ Warning problems: {output['warning_problem_count']}")
    print(f"✅ Analytic frameworks: {output['analytic_framework_count']}")
    print(f"✅ Indicator groups: {output['indicator_group_count']}")
    print(f"✅ Indicator references: {output['mapped_indicator_reference_count']}")
    print("✅ PRECURSOR / ACCELERANT / TRIGGER / CONTRA coverage validated")

if __name__ == "__main__":
    main()
