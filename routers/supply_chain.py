from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any, Optional

from services.apis.gdelt_api import fetch_gdelt_signals
from services.apis.ofac_api import fetch_ofac_sanctions
from services.apis.eia_api import fetch_eia_energy_signals
from app.services.simulation_question_generator import generate_simulation_questions
from services.supply_chain_live_fetchers import fetch_live_supply_chain_sources
from services.supply_chain_signal_extractor import extract_supply_chain_signals


router = APIRouter(prefix="/api/supply-chain", tags=["Supply Chain Risk"])


CHOKEPOINTS = [
    {
        "id": "hormuz",
        "name": "Strait of Hormuz",
        "region": "Persian Gulf",
        "countries": ["Iran", "Oman", "United Arab Emirates"],
        "risk_score": 84,
        "risk_level": "Critical",
        "affected_commodities": ["Oil", "LNG", "Refined Petroleum"],
        "affected_routes": ["Gulf energy exports to Asia", "Gulf energy exports to Europe"],
        "affected_sectors": ["Energy", "Shipping", "Manufacturing", "Defense"],
        "primary_drivers": [
            "Naval activity",
            "Iran-U.S. tensions",
            "Tanker insurance premiums",
            "Energy price volatility",
            "Limited rerouting capacity"
        ],
        "recent_signals": [
            "Elevated maritime security concerns",
            "Energy-market sensitivity",
            "Strategic chokepoint concentration"
        ],
        "forecast_7d": "Elevated",
        "forecast_30d": "High",
        "forecast_90d": "Persistent elevated risk",
        "confidence": "Medium-High"    },
    {
        "id": "taiwan-strait",
        "name": "Taiwan Strait",
        "region": "Indo-Pacific",
        "countries": ["Taiwan", "China", "Japan", "United States"],
        "risk_score": 79,
        "risk_level": "High",
        "affected_commodities": ["Semiconductors", "Electronics", "Advanced Manufacturing Inputs"],
        "affected_routes": ["Western Pacific shipping routes", "East Asia technology supply chain"],
        "affected_sectors": ["Semiconductors", "Electronics", "Manufacturing", "Defense"],
        "primary_drivers": [
            "Military exercises",
            "Export controls",
            "U.S.-China rivalry",
            "Semiconductor production concentration"
        ],
        "recent_signals": [
            "Military signaling",
            "Technology export control pressure",
            "Alliance coordination"
        ],
        "forecast_7d": "Moderate",
        "forecast_30d": "High",
        "forecast_90d": "Structurally elevated",
        "confidence": "Medium"    },
    {
        "id": "bab-el-mandeb",
        "name": "Bab el-Mandeb",
        "region": "Red Sea / Gulf of Aden",
        "countries": ["Yemen", "Djibouti", "Eritrea"],
        "risk_score": 82,
        "risk_level": "Critical",
        "affected_commodities": ["Oil", "LNG", "Containers", "Food"],
        "affected_routes": ["Red Sea shipping corridor", "Asia-Europe maritime route"],
        "affected_sectors": ["Shipping", "Energy", "Food", "Manufacturing"],
        "primary_drivers": [
            "Armed group activity",
            "Vessel attack risk",
            "Insurance premium pressure",
            "Shipping rerouting"
        ],
        "recent_signals": [
            "Alternative routing around Cape of Good Hope",
            "Heightened maritime advisories",
            "Regional conflict spillover"
        ],
        "forecast_7d": "High",
        "forecast_30d": "High",
        "forecast_90d": "Persistent conflict-linked risk",
        "confidence": "Medium-High"    },
    {
        "id": "suez",
        "name": "Suez Canal",
        "region": "Egypt / Eastern Mediterranean",
        "countries": ["Egypt"],
        "risk_score": 68,
        "risk_level": "Moderate-High",
        "affected_commodities": ["Containers", "Oil", "LNG", "Manufactured Goods"],
        "affected_routes": ["Asia-Europe trade route", "Mediterranean-Red Sea corridor"],
        "affected_sectors": ["Shipping", "Energy", "Retail", "Manufacturing"],
        "primary_drivers": [
            "Red Sea instability",
            "Shipping rerouting",
            "Transit reliability concerns",
            "Insurance cost sensitivity"
        ],
        "recent_signals": [
            "Route diversion pressure",
            "Regional security uncertainty",
            "Transit dependency exposure"
        ],
        "forecast_7d": "Moderate",
        "forecast_30d": "Elevated",
        "forecast_90d": "Dependent on Red Sea security environment",
        "confidence": "Medium"    }
]


INDICATORS = [
    {
        "category": "Chokepoint Risk",
        "indicator_name": "Shipping Rerouting Frequency",
        "indicator_code": "shipping_rerouting_frequency",
        "current_value": 67,
        "direction": "Rising",
        "severity": "High",
        "confidence": "Medium",        "source_type": "AIS / shipping data",
        "methodology_note": "Rising rerouting may indicate disruption, insurance concerns, or conflict avoidance behavior."
    },
    {
        "category": "Energy Supply",
        "indicator_name": "Oil Transit Exposure",
        "indicator_code": "oil_transit_exposure",
        "current_value": 82,
        "direction": "Rising",
        "severity": "Critical",
        "confidence": "High",        "source_type": "Energy market / trade data",
        "methodology_note": "High oil transit exposure increases vulnerability to chokepoint disruption and price shocks."
    },
    {
        "category": "Commodity Dependency",
        "indicator_name": "Semiconductor Concentration Exposure",
        "indicator_code": "semiconductor_concentration_exposure",
        "current_value": 79,
        "direction": "Stable",
        "severity": "High",
        "confidence": "Medium-High",        "source_type": "Trade / industrial concentration data",
        "methodology_note": "Measures exposure to concentrated semiconductor production and transit corridors."
    },
    {
        "category": "Logistics and Ports",
        "indicator_name": "Port and Vessel Delay Index",
        "indicator_code": "vessel_delay_index",
        "current_value": 61,
        "direction": "Rising",
        "severity": "Moderate",
        "confidence": "Medium",        "source_type": "Port / shipping data",
        "methodology_note": "Delay increases can signal congestion, rerouting pressure, or operational disruption."
    },
    {
        "category": "Sanctions and Trade",
        "indicator_name": "Export Control Exposure",
        "indicator_code": "export_control_exposure",
        "current_value": 74,
        "direction": "Rising",
        "severity": "High",
        "confidence": "Medium",        "source_type": "Sanctions / trade policy data",
        "methodology_note": "Tracks exposure to restrictions affecting dual-use, technology, energy, and strategic commodities."
    }
]


def find_chokepoint(name: Optional[str]) -> Optional[Dict[str, Any]]:
    if not name:
        return None

    name_lower = name.lower()

    for chokepoint in CHOKEPOINTS:
        if name_lower in chokepoint["name"].lower() or chokepoint["name"].lower() in name_lower:
            return chokepoint

    return None


def classify_global_risk(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 50:
        return "Moderate"
    if score >= 25:
        return "Low"
    return "Minimal"

@router.get("/overview")
def get_supply_chain_overview():

    global_score = round(
        sum(item["risk_score"] for item in CHOKEPOINTS) / len(CHOKEPOINTS)
    )

    top_dependencies = sorted(
        list({
            commodity
            for item in CHOKEPOINTS
            for commodity in item["affected_commodities"]
        })
    )[:6]

    result = {
        "region": "Global maritime chokepoints",
        "topic": "supply chain and chokepoint risk",
        "executive_judgment": "Global supply chain risk is elevated due to critical chokepoint exposure across Hormuz, Bab el-Mandeb, Taiwan Strait, and Suez Canal.",

        "global_score": global_score,
        "risk_level": classify_global_risk(global_score),
        "active_chokepoint_alerts": len(
            [item for item in CHOKEPOINTS if item["risk_score"] >= 70]
        ),
        "critical_dependency_exposure": top_dependencies,
        "disruption_probability_30d": min(round(global_score * 0.55), 95),
        "top_risks": sorted(
            CHOKEPOINTS,
            key=lambda x: x["risk_score"],
            reverse=True
        )[:3]
    }

    simulation_questions = generate_simulation_questions(result)

    return {
        "engine": "sovereign_supply_chain_risk",
        "status": "success",
        "last_updated": datetime.utcnow().isoformat(),
        "data": result,
        "simulation_questions": simulation_questions
    }


@router.get("/chokepoints")
def get_chokepoints():

    result = {
        "region": "Global maritime chokepoints",
        "topic": "critical trade and supply chain disruption analysis",
        "executive_judgment": (
            "Multiple global maritime chokepoints are experiencing elevated "
            "geopolitical and supply-chain disruption risks affecting energy, "
            "shipping, manufacturing, and strategic trade flows."
        ),
        "count": len(CHOKEPOINTS),
        "data": CHOKEPOINTS
    }

    simulation_questions = generate_simulation_questions(result)

    return {
        "status": "success",
        "count": len(CHOKEPOINTS),
        "data": CHOKEPOINTS,
        "simulation_questions": simulation_questions
    }

@router.get("/indicators")
def get_indicators():
    return {
        "status": "success",
        "count": len(INDICATORS),
        "data": INDICATORS
    }


@router.post("/run-agent")
def run_supply_chain_agent(payload: dict):

    selected_country = payload.get("selected_country")
    selected_sector = payload.get("selected_sector")
    selected_chokepoint = payload.get("selected_chokepoint")
    selected_commodity = payload.get("selected_commodity")

    live_data = fetch_live_supply_chain_sources(
        country=selected_country,
        sector=selected_sector,
        chokepoint=selected_chokepoint,
        commodity=selected_commodity
    )

    signal_result = extract_supply_chain_signals(live_data)
    live_signals = signal_result.get("signals", {})
    extracted_signals = signal_result.get("extracted_signals", [])

    risk_score = 35
    drivers = []
    affected_sectors = []
    convergence_score = 0

    if selected_country in ["China", "Taiwan"]:
        risk_score += 18
        drivers.append("High geopolitical exposure")
        convergence_score += 1

    if selected_country in ["Russia", "Iran"]:
        risk_score += 20
        drivers.append("Sanctions and geopolitical pressure")
        convergence_score += 1

    if selected_sector == "semiconductors":
        risk_score += 15
        affected_sectors.append("Technology")
        drivers.append("Semiconductor dependency risk")
        convergence_score += 1

    if selected_sector == "energy":
        risk_score += 14
        affected_sectors.append("Energy")
        drivers.append("Energy market volatility")
        convergence_score += 1

    if selected_chokepoint in [
        "Taiwan Strait",
        "Strait of Hormuz",
        "Bab el-Mandeb",
        "South China Sea"
    ]:
        risk_score += 20
        drivers.append(f"Strategic chokepoint exposure: {selected_chokepoint}")
        convergence_score += 1

    if selected_commodity:
        risk_score += 8
        drivers.append(f"Commodity disruption risk: {selected_commodity}")

    if live_signals.get("military_escalation"):
        risk_score += 12
        drivers.append("Live signal: military escalation")

    if live_signals.get("port_disruption"):
        risk_score += 10
        drivers.append("Live signal: port disruption")

    if live_signals.get("sanctions_expansion"):
        risk_score += 10
        drivers.append("Live signal: sanctions or restrictions")

    risk_score = min(risk_score, 100)

    if risk_score >= 85:
        level = "Critical"
    elif risk_score >= 70:
        level = "High"
    elif risk_score >= 50:
        level = "Elevated"
    elif risk_score >= 30:
        level = "Watch"
    else:
        level = "Stable"

    forecast = {
        "7_day": min(100, risk_score - 8),
        "30_day": risk_score,
        "90_day": min(100, risk_score + 6)
    }

    executive_judgment = (
        f"{selected_country} shows {level.lower()} supply-chain risk "
        f"with exposure across strategic sectors and logistics networks."
    )

    return {
        "status": "success",
        "agent_type": "full_supply_chain_briefing_agent_v3",
        "selected_target": selected_country,
        "input_context": {
            "selected_country": selected_country,
            "selected_sector": selected_sector,
            "selected_chokepoint": selected_chokepoint,
            "selected_commodity": selected_commodity,
            "time_horizon": "30 days"
        },
        "output": {
            "executive_judgment": executive_judgment,
            "risk_score": risk_score,
            "risk_level": level,
            "forecast": forecast,
            "convergence_score": convergence_score,
            "main_drivers": drivers,
            "affected_sectors": affected_sectors,
            "confidence": "Medium-High",

            "live_signals": live_signals,
            "extracted_signals": extracted_signals,
            "live_sources": live_data.get("source_status", {}),
            "live_articles": live_data.get("gdelt_news", []),

            "recommended_actions": [
                "Review supplier and route exposure",
                "Stress-test logistics continuity",
                "Identify alternative sourcing pathways",
                "Monitor escalation indicators",
                "Run simulation scenarios"
            ],

            "simulation_questions": [
                "What happens if this chokepoint closes for 7 days?",
                "Which firms and sectors are most exposed?",
                "What second-order effects impact global markets?",
                "Which alternative routes reduce disruption risk?"
            ]
        }
    }



@router.get("/external/gdelt")
def get_external_gdelt(query: str = "supply chain disruption", maxrecords: int = 20):
    return {
        "status": "success",
        "source": "gdelt",
        "data": fetch_gdelt_signals(query=query, maxrecords=maxrecords)
    }


@router.get("/external/ofac")
def get_external_ofac(limit: int = 25):
    return {
        "status": "success",
        "source": "ofac",
        "data": fetch_ofac_sanctions(limit=limit)
    }


@router.get("/external/eia")
def get_external_eia():
    return {
        "status": "success",
        "source": "eia",
        "data": fetch_eia_energy_signals()
    }


@router.get("/live-signals")
def get_live_supply_chain_signals(query: str = "Strait of Hormuz shipping oil sanctions"):
    gdelt = fetch_gdelt_signals(query=query, maxrecords=10)
    ofac = fetch_ofac_sanctions(limit=10)
    eia = fetch_eia_energy_signals()

    return {
        "status": "success",
        "query": query,
        "sources_used": ["gdelt", "ofac", "eia"],
        "data": {
            "gdelt_signals": gdelt,
            "ofac_signals": ofac,
            "eia_signals": eia
        }
    }


@router.post("/fusion-report")
def generate_supply_chain_fusion_report(payload: dict):
    agent_type = "full_supply_chain_fusion_report"

    selected_chokepoint = payload.get("selected_chokepoint") or "Strait of Hormuz"
    selected_country = payload.get("selected_country")
    selected_commodity = payload.get("selected_commodity") or "Oil"
    selected_sector = payload.get("selected_sector")
    selected_route = payload.get("selected_route")
    time_horizon = payload.get("time_horizon", "30 days")

    matched_chokepoint = find_chokepoint(selected_chokepoint)

    gdelt_signals = fetch_gdelt_signals(
        query=f"{selected_chokepoint} {selected_commodity} shipping disruption",
        maxrecords=5
    )

    ofac_signals = fetch_ofac_sanctions(limit=5)
    eia_signals = fetch_eia_energy_signals()

    if matched_chokepoint:
        target_name = matched_chokepoint["name"]
        risk_score = matched_chokepoint["risk_score"]
        risk_level = matched_chokepoint["risk_level"]
        drivers = matched_chokepoint["primary_drivers"]
        commodities = matched_chokepoint["affected_commodities"]
        routes = matched_chokepoint["affected_routes"]
        sectors = matched_chokepoint["affected_sectors"]
        confidence = matched_chokepoint["confidence"]
        forecast = {
            "7_day": matched_chokepoint["forecast_7d"],
            "30_day": matched_chokepoint["forecast_30d"],
            "90_day": matched_chokepoint["forecast_90d"]
        }
    else:
        target_name = selected_chokepoint
        risk_score = 72
        risk_level = "High"
        drivers = [
            "Supply chain concentration",
            "Geopolitical exposure",
            "Energy market sensitivity",
            "Limited substitution capacity"
        ]
        commodities = [selected_commodity]
        routes = [selected_route or "Route exposure requires additional data"]
        sectors = [selected_sector or "Energy", "Shipping", "Manufacturing"]
        confidence = "Medium"
        forecast = {
            "7_day": "Moderate",
            "30_day": "Elevated",
            "90_day": "Uncertain"
        }

    return {
        "status": "success",
        "report_type": "supply_chain_fusion_report",
        "selected_target": target_name,
        "time_horizon": time_horizon,
        "input_context": {
            "selected_chokepoint": selected_chokepoint,
            "selected_country": selected_country,
            "selected_commodity": selected_commodity,
            "selected_sector": selected_sector,
            "selected_route": selected_route,
            "time_horizon": time_horizon
        },
        "overall_assessment": {
            "executive_judgment": (
                f"{target_name} presents {risk_level.lower()} supply chain risk over the "
                f"{time_horizon} horizon. The fused assessment combines chokepoint exposure, "
                f"energy-market sensitivity, sanctions exposure, live event signals, and route disruption risk."
            ),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": confidence        },
        "external_signals": {
            "gdelt": gdelt_signals,
            "ofac": ofac_signals,
            "eia": eia_signals
        },
        "fusion_findings": [
            f"{target_name} is exposed to disruption through {', '.join(commodities)} flows.",
            f"Primary risk drivers include {', '.join(drivers[:3])}.",
            "Energy price sensitivity and freight disruption are likely transmission channels.",
            "Sanctions and export-control exposure should be monitored alongside physical route disruption.",
            "A sustained disruption could affect procurement timelines, insurance costs, and market volatility."
        ],
        "affected_commodities": commodities,
        "affected_routes": routes,
        "affected_sectors": sectors,
        "main_drivers": drivers,
        "forecast": forecast,
        "early_warning_indicators": [
            "Sudden vessel rerouting",
            "Insurance premium spike",
            "Oil or LNG price volatility",
            "Naval warnings or maritime advisories",
            "Sanctions announcements",
            "Port delay or vessel queue increases",
            "Diplomatic escalation involving affected states"
        ],
        "decision_implications": {
            "investors": [
                "Monitor exposed energy, shipping, insurance, and manufacturing equities.",
                "Stress-test commodity price volatility and inflation pass-through."
            ],
            "corporates": [
                "Review supplier concentration and alternative sourcing options.",
                "Assess inventory buffers and procurement timelines."
            ],
            "government": [
                "Monitor maritime security, sanctions exposure, and alliance coordination.",
                "Prepare early warning briefs for escalation scenarios."
            ],
            "logistics": [
                "Compare alternative routes and rerouting costs.",
                "Monitor port congestion, vessel delays, and insurance conditions."
            ]
        },
        "intelligence_gaps": [
            "Live AIS vessel movement data",
            "Real-time insurance premium data",
            "Supplier-level exposure data",
            "Confirmed port congestion feeds",
            "Licensed commodity and freight pricing feeds"
        ],
        "recommended_actions": [
            "Run scenario simulation for 7, 14, and 30-day disruption cases.",
            "Compare alternative routes and exposed commodities.",
            "Monitor OFAC, EIA, and GDELT signals daily.",
            "Build supplier-level exposure scoring.",
            "Generate executive decision brief for affected sectors."
        ]
    }
