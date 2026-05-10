from typing import Dict, Any, List


SECTOR_DEFINITIONS = [
    {
        "sector": "Geopolitical Escalation",
        "description": "Tracks interstate tension, diplomatic breakdown, military signaling, coercive pressure, and crisis escalation.",
        "keywords": [
            "war", "military", "border", "missile", "sanctions", "diplomatic",
            "embassy", "threat", "invasion", "mobilization", "naval", "airspace",
            "escalation", "deterrence"
        ],
        "relevant_modules": [
            "Global Strategic Risk Map",
            "Regional Intelligence Dashboard",
            "Run Geopolitical Agent",
            "Scenario Simulation Lab",
            "Strategic Early Warning System"
        ],
    },
    {
        "sector": "Security & Conflict",
        "description": "Tracks armed conflict, terrorism, coups, civil unrest, insurgency, border incidents, and internal instability.",
        "keywords": [
            "attack", "terror", "explosion", "coup", "insurgency", "riot",
            "protest", "clashes", "militia", "armed", "violence", "unrest",
            "security forces", "casualties"
        ],
        "relevant_modules": [
            "Run Security Analysis Agent",
            "Regional Intelligence Dashboard",
            "Global Strategic Risk Map",
            "Scenario Simulation Lab",
            "Strategic Early Warning System"
        ],
    },
    {
        "sector": "Energy & Commodity Risk",
        "description": "Tracks oil, gas, LNG, chokepoints, critical minerals, commodity shocks, and resource nationalism.",
        "keywords": [
            "oil", "gas", "lng", "energy", "pipeline", "tanker", "hormuz",
            "suez", "commodity", "rare earth", "mineral", "refinery",
            "opec", "price spike", "supply disruption"
        ],
        "relevant_modules": [
            "Run Energy Analysis Agent",
            "Global Supply Chain Risk Engine",
            "Corporate Exposure & Portfolio Intelligence",
            "Scenario Simulation Lab",
            "Global Strategic Risk Map"
        ],
    },
    {
        "sector": "Supply Chain & Trade Disruption",
        "description": "Tracks maritime corridors, ports, sanctions, export controls, critical minerals, and logistics disruption.",
        "keywords": [
            "shipping", "port", "trade", "export control", "import", "supply chain",
            "logistics", "container", "maritime", "freight", "chokepoint",
            "red sea", "taiwan strait", "suez", "blockade"
        ],
        "relevant_modules": [
            "Global Supply Chain Risk Engine",
            "Corporate Exposure & Portfolio Intelligence",
            "Scenario Simulation Lab",
            "Global Strategic Risk Map",
            "Run Geopolitical Agent"
        ],
    },
    {
        "sector": "Cyber & Information Operations",
        "description": "Tracks cyberattacks, disinformation, election interference, deepfakes, influence operations, and infrastructure targeting.",
        "keywords": [
            "cyber", "hack", "malware", "ransomware", "cve", "vulnerability",
            "disinformation", "deepfake", "propaganda", "influence operation",
            "information warfare", "critical infrastructure"
        ],
        "relevant_modules": [
            "Cyber & Information Risk Layer",
            "Strategic Early Warning System",
            "Scenario Simulation Lab",
            "Corporate Exposure & Portfolio Intelligence"
        ],
    },
    {
        "sector": "Economic & Financial Stress",
        "description": "Tracks inflation, currency pressure, sovereign debt, sanctions exposure, capital flight, and market volatility.",
        "keywords": [
            "inflation", "currency", "debt", "default", "capital flight",
            "interest rate", "market", "banking", "financial crisis",
            "sanctions", "recession", "sovereign risk"
        ],
        "relevant_modules": [
            "Corporate Exposure & Portfolio Intelligence",
            "Regional Intelligence Dashboard",
            "Scenario Simulation Lab",
            "Global Strategic Risk Map",
            "Strategic Early Warning System"
        ],
    },
    {
        "sector": "Political Stability & Governance",
        "description": "Tracks protests, election instability, elite fragmentation, legitimacy crisis, repression, and policy shocks.",
        "keywords": [
            "election", "protest", "government", "parliament", "president",
            "repression", "opposition", "legitimacy", "corruption", "policy shock",
            "state of emergency", "civil society"
        ],
        "relevant_modules": [
            "Run Geopolitical Agent",
            "Regional Intelligence Dashboard",
            "Scenario Simulation Lab",
            "Strategic Early Warning System"
        ],
    },
    {
        "sector": "Corporate & Portfolio Exposure",
        "description": "Tracks company exposure, asset exposure, operational risk, supply-chain dependencies, insurance risk, and investor impact.",
        "keywords": [
            "company", "corporate", "asset", "portfolio", "insurance", "operations",
            "factory", "investment", "market exposure", "supply dependency",
            "sanctions exposure", "business disruption"
        ],
        "relevant_modules": [
            "Corporate Exposure & Portfolio Intelligence",
            "Global Supply Chain Risk Engine",
            "Scenario Simulation Lab",
            "Run Energy Analysis Agent",
            "Strategic Early Warning System"
        ],
    },
]


def classify_warning_level(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 50:
        return "Elevated"
    if score >= 30:
        return "Watch"
    return "Low"


def classify_signal_noise(score: int, has_system_notice: bool = False) -> Dict[str, str]:
    if has_system_notice:
        return {
            "classification": "Insufficient Live Data",
            "judgment": "Live external signal access is limited. The system is relying on structured analytical logic and available memory rather than full real-time corroboration.",
            "meaning": "This should not be treated as absence of risk. It means the live feed needs corroboration from additional APIs or saved intelligence memory."
        }

    if score >= 85:
        return {
            "classification": "Strong Signal",
            "judgment": "The warning pattern is repeated, strategically meaningful, and consistent with known escalation pathways.",
            "meaning": "This is decision-relevant and should trigger senior review or automated alerting."
        }

    if score >= 70:
        return {
            "classification": "Signal",
            "judgment": "The warning appears relevant and actionable, with enough severity and momentum to justify escalation.",
            "meaning": "Users should monitor closely and consider running scenario and exposure analysis."
        }

    if score >= 50:
        return {
            "classification": "Emerging Signal",
            "judgment": "The warning is not yet a crisis, but patterns are becoming relevant enough for active monitoring.",
            "meaning": "Users should track changes, compare with structured datasets, and build a watch timeline."
        }

    if score >= 30:
        return {
            "classification": "Mixed Signal",
            "judgment": "The warning contains some relevant indicators, but the evidence is partial, isolated, or not yet corroborated.",
            "meaning": "Users should avoid overreaction but continue monitoring for repetition and escalation."
        }

    return {
        "classification": "Noise / Low Signal",
        "judgment": "Current signals are weak, isolated, or low-confidence.",
        "meaning": "No immediate action is required beyond routine monitoring."
    }


def score_sector_from_signals(
    sector: Dict[str, Any],
    signals: List[Dict[str, Any]],
    base_score: int
) -> int:
    text_blob = " ".join(
        [
            f"{signal.get('title', '')} {signal.get('summary', '')}".lower()
            for signal in signals
        ]
    )

    keyword_hits = 0
    for keyword in sector["keywords"]:
        if keyword.lower() in text_blob:
            keyword_hits += 1

    score = base_score

    if keyword_hits >= 6:
        score += 18
    elif keyword_hits >= 4:
        score += 12
    elif keyword_hits >= 2:
        score += 7
    elif keyword_hits >= 1:
        score += 4
    else:
        score -= 6

    return max(0, min(score, 100))


def build_sector_alerts(
    country: str,
    topic: str,
    overall_score: int,
    signals: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    has_system_notice = any(
        signal.get("source") == "system" or signal.get("category") == "system_notice"
        for signal in signals
    )

    sector_alerts = []

    for sector in SECTOR_DEFINITIONS:
        sector_score = score_sector_from_signals(sector, signals, overall_score)
        sector_status = classify_warning_level(sector_score)
        signal_noise = classify_signal_noise(sector_score, has_system_notice)

        sector_alerts.append(
            {
                "sector": sector["sector"],
                "description": sector["description"],
                "score": sector_score,
                "status": sector_status,
                "signal_or_noise": signal_noise["classification"],
                "signal_noise_judgment": signal_noise["judgment"],
                "current_assessment": build_current_assessment(
                    country=country,
                    topic=topic,
                    sector=sector["sector"],
                    score=sector_score,
                    status=sector_status,
                    has_system_notice=has_system_notice,
                ),
                "what_might_happen": build_what_might_happen(sector["sector"], country, topic),
                "monitoring_indicators": build_sector_monitoring_indicators(sector["sector"], country, topic),
                "recommended_actions": build_sector_recommended_actions(sector["sector"]),
                "relevant_modules": sector["relevant_modules"],
            }
        )

    return sorted(sector_alerts, key=lambda x: x["score"], reverse=True)


def build_current_assessment(
    country: str,
    topic: str,
    sector: str,
    score: int,
    status: str,
    has_system_notice: bool
) -> str:
    if has_system_notice:
        return (
            f"{sector} for {country} is under structured monitoring for {topic}, "
            f"but live external signals are currently limited. The system is maintaining a {status.lower()} posture "
            f"based on available indicators, known escalation pathways, and analytical framework scoring."
        )

    return (
        f"{sector} for {country} is currently assessed at {status.lower()} warning posture "
        f"for {topic}. The score reflects sector relevance, signal language, potential spillover, and escalation sensitivity."
    )


def build_what_might_happen(sector: str, country: str, topic: str) -> List[str]:
    if sector == "Energy & Commodity Risk":
        return [
            "Oil, gas, LNG, or commodity price volatility may increase.",
            "Shipping insurance or transport costs may rise.",
            "Energy infrastructure or maritime chokepoints may become more exposed.",
            "Corporate and sovereign energy exposure may require reassessment."
        ]

    if sector == "Supply Chain & Trade Disruption":
        return [
            "Trade routes, ports, or maritime corridors may face disruption.",
            "Export controls or sanctions may affect exposed sectors.",
            "Logistics delays may create second-order effects for companies and investors.",
            "Critical mineral or semiconductor dependencies may become more visible."
        ]

    if sector == "Cyber & Information Operations":
        return [
            "Cyber activity may target public institutions, firms, or critical infrastructure.",
            "Disinformation or deepfake activity may increase around the crisis.",
            "Attribution ambiguity may complicate response options.",
            "Information operations may distort public perception and investor confidence."
        ]

    if sector == "Economic & Financial Stress":
        return [
            "Currency, inflation, or debt pressures may intensify.",
            "Sanctions or market volatility may affect capital flows.",
            "Investor exposure may require reassessment.",
            "Financial stress may spill into political or social instability."
        ]

    if sector == "Security & Conflict":
        return [
            "Localized incidents may become repeated or clustered.",
            "Security forces, militias, or armed actors may escalate activity.",
            "Civil unrest or violence may spread geographically.",
            "A triggering incident may change the warning level quickly."
        ]

    if sector == "Political Stability & Governance":
        return [
            "Protests, elite fragmentation, or legitimacy challenges may intensify.",
            "Election or governance disputes may create instability.",
            "Government repression or emergency measures may increase.",
            "Policy shocks may affect companies, markets, or diplomatic posture."
        ]

    if sector == "Corporate & Portfolio Exposure":
        return [
            "Exposed firms, assets, supply chains, or investments may face operational risk.",
            "Insurance, compliance, and sanctions exposure may increase.",
            "Portfolio sensitivity to the country or sector may rise.",
            "Decision-makers may need scenario and exposure analysis."
        ]

    return [
        "Diplomatic pressure, military signaling, or coercive behavior may intensify.",
        "Regional actors may adjust posture in response to perceived escalation.",
        "A trigger event may rapidly increase strategic risk.",
        "Cross-domain spillover may affect energy, markets, cyber, or supply chains."
    ]


def build_sector_monitoring_indicators(sector: str, country: str, topic: str) -> List[Dict[str, str]]:
    common = [
        {
            "indicator": f"Increase in reporting volume related to {topic} in {country}",
            "relevance": "Medium",
            "status": "Monitoring",
            "escalation_threshold": "Escalate if reporting volume rises across multiple independent sources."
        },
        {
            "indicator": "Shift from rhetoric to operational activity",
            "relevance": "High",
            "status": "Monitoring",
            "escalation_threshold": "Escalate if statements are followed by military, cyber, economic, or coercive actions."
        },
    ]

    sector_specific = {
        "Energy & Commodity Risk": [
            {
                "indicator": "Oil, gas, LNG, or commodity price movement linked to the crisis",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if price movement coincides with confirmed disruption or threat reporting."
            },
            {
                "indicator": "Chokepoint, tanker, pipeline, or port disruption",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Immediate escalation if confirmed by multiple sources."
            },
        ],
        "Supply Chain & Trade Disruption": [
            {
                "indicator": "Shipping delays, port closures, insurance premium changes, or rerouting",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if disruption affects major trade corridors or critical goods."
            }
        ],
        "Cyber & Information Operations": [
            {
                "indicator": "Cyber incident, disinformation campaign, deepfake, or infrastructure targeting",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if incident affects critical infrastructure, elections, markets, or public trust."
            }
        ],
        "Security & Conflict": [
            {
                "indicator": "Repeated armed incidents, attacks, troop movement, or protest violence",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if incidents cluster geographically or involve state/security actors."
            }
        ],
    }

    return common + sector_specific.get(sector, [])


def build_sector_recommended_actions(sector: str) -> List[str]:
    actions = [
        "Continue live signal tracking.",
        "Corroborate against structured datasets and saved intelligence memory.",
        "Escalate if warning score rises above 70.",
    ]

    if sector == "Energy & Commodity Risk":
        actions += [
            "Run Energy Analysis Agent.",
            "Run Supply Chain Risk Engine.",
            "Generate Corporate Exposure Report for energy-sensitive assets."
        ]
    elif sector == "Supply Chain & Trade Disruption":
        actions += [
            "Run Global Supply Chain Risk Engine.",
            "Check chokepoint, port, sanctions, and commodity dependencies.",
            "Run Scenario Simulation Lab for disruption pathways."
        ]
    elif sector == "Cyber & Information Operations":
        actions += [
            "Monitor cyber advisories and vulnerability feeds.",
            "Assess information manipulation and disinformation risk.",
            "Run scenario analysis for cyber-enabled escalation."
        ]
    elif sector == "Corporate & Portfolio Exposure":
        actions += [
            "Run Corporate Exposure & Portfolio Intelligence.",
            "Assess affected sectors, assets, counterparties, and insurance exposure.",
            "Generate executive exposure brief."
        ]
    else:
        actions += [
            "Run Geopolitical or Security Analysis Agent.",
            "Run Scenario Simulation Lab.",
            "Update Global Strategic Risk Map layer."
        ]

    return actions


def build_monitoring_indicators_by_category(
    country: str,
    topic: str
) -> Dict[str, List[Dict[str, str]]]:
    return {
        "Military/Security": [
            {
                "indicator": "Troop movement, missile/drone activity, attacks, or border incidents",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if confirmed movement or attack is reported by multiple sources."
            }
        ],
        "Diplomatic/Political": [
            {
                "indicator": "Diplomatic breakdown, sanctions announcement, embassy warning, or emergency meeting",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if diplomatic signaling shifts from rhetoric to formal action."
            }
        ],
        "Economic/Market": [
            {
                "indicator": "Currency movement, inflation pressure, market volatility, sanctions exposure",
                "relevance": "Medium",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if market stress aligns with security or political indicators."
            }
        ],
        "Energy/Supply Chain": [
            {
                "indicator": "Port disruption, tanker incident, chokepoint risk, oil/gas price volatility",
                "relevance": "High",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if physical disruption or credible threat affects a major corridor."
            }
        ],
        "Cyber/Information": [
            {
                "indicator": "Cyberattack, vulnerability exploitation, disinformation, deepfake, influence operation",
                "relevance": "Medium",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if linked to critical infrastructure, election integrity, or state-backed activity."
            }
        ],
        "Social/Local Stability": [
            {
                "indicator": "Protests, riots, repression, elite fragmentation, civil unrest",
                "relevance": "Medium",
                "status": "Monitoring",
                "escalation_threshold": "Escalate if unrest spreads across cities or involves security-force violence."
            }
        ],
    }


def build_recommended_decision_actions() -> Dict[str, List[str]]:
    return {
        "Monitor": [
            "Continue live signal tracking.",
            "Watch for repeated indicators rather than isolated claims.",
            "Compare current signals with historical patterns."
        ],
        "Corroborate": [
            "Validate against GDELT, ACLED, sanctions, energy, cyber, and market data.",
            "Check source reliability and cross-source repetition.",
            "Separate official reporting from social amplification."
        ],
        "Escalate": [
            "Escalate if warning score exceeds 70.",
            "Notify analyst or decision-maker if a trigger indicator is confirmed.",
            "Generate executive brief if cross-domain spillover is detected."
        ],
        "Simulate": [
            "Run Scenario Simulation Lab.",
            "Test baseline, deterioration, and strategic shock pathways.",
            "Estimate second-order effects across markets, supply chains, and security."
        ],
        "Assess Exposure": [
            "Run Corporate Exposure & Portfolio Intelligence.",
            "Run Supply Chain Risk Engine.",
            "Run Energy Analysis Agent if energy, chokepoint, or commodity exposure is present."
        ],
    }


def infer_relevant_modules_from_topic(topic: str, sector_alerts: List[Dict[str, Any]]) -> List[str]:
    topic_lower = topic.lower()
    modules = set()

    for alert in sector_alerts[:3]:
        for module in alert.get("relevant_modules", []):
            modules.add(module)

    if any(word in topic_lower for word in ["oil", "gas", "hormuz", "energy", "lng", "chokepoint", "shipping"]):
        modules.update([
            "Run Energy Analysis Agent",
            "Global Supply Chain Risk Engine",
            "Corporate Exposure & Portfolio Intelligence",
            "Scenario Simulation Lab"
        ])

    if any(word in topic_lower for word in ["cyber", "deepfake", "disinformation", "information"]):
        modules.update([
            "Cyber & Information Risk Layer",
            "Scenario Simulation Lab",
            "Corporate Exposure & Portfolio Intelligence"
        ])

    if any(word in topic_lower for word in ["protest", "election", "coup", "governance"]):
        modules.update([
            "Run Geopolitical Agent",
            "Run Security Analysis Agent",
            "Regional Intelligence Dashboard",
            "Scenario Simulation Lab"
        ])

    return sorted(modules)
