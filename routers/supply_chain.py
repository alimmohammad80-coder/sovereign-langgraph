from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/supply-chain", tags=["Supply Chain Risk"])


@router.get("/overview")
def get_supply_chain_overview():
    return {
        "engine": "sovereign_supply_chain_risk",
        "status": "success",
        "last_updated": datetime.utcnow().isoformat(),
        "data": {
            "global_score": 72,
            "risk_level": "High",
            "active_chokepoint_alerts": 6,
            "critical_dependency_exposure": [
                "Semiconductors",
                "Rare Earths",
                "LNG"
            ],
            "disruption_probability_30d": 38
        }
    }


@router.get("/chokepoints")
def get_chokepoints():
    return {
        "status": "success",
        "data": [
            {
                "id": "hormuz",
                "name": "Strait of Hormuz",
                "region": "Persian Gulf",
                "risk_score": 84,
                "risk_level": "Critical",
                "affected_commodities": ["Oil", "LNG"],
                "primary_drivers": [
                    "Naval activity",
                    "Iran-U.S. tensions",
                    "Insurance premiums"
                ],
                "confidence": "Medium-High"
            },
            {
                "id": "taiwan-strait",
                "name": "Taiwan Strait",
                "region": "Indo-Pacific",
                "risk_score": 79,
                "risk_level": "High",
                "affected_commodities": [
                    "Semiconductors",
                    "Electronics"
                ],
                "primary_drivers": [
                    "Military exercises",
                    "Export controls",
                    "U.S.-China rivalry"
                ],
                "confidence": "Medium"
            }
        ]
    }


@router.get("/indicators")
def get_indicators():
    return {
        "status": "success",
        "data": [
            {
                "category": "Chokepoint Risk",
                "indicator_name": "Shipping Rerouting Frequency",
                "current_value": 67,
                "direction": "Rising",
                "severity": "High",
                "confidence": "Medium",
                "source_type": "AIS / shipping data"
            },
            {
                "category": "Energy Supply",
                "indicator_name": "Oil Transit Exposure",
                "current_value": 82,
                "direction": "Rising",
                "severity": "Critical",
                "confidence": "High",
                "source_type": "Energy market / trade data"
            }
        ]
    }


@router.post("/run-agent")
def run_supply_chain_agent(payload: dict):
    selected_target = (
        payload.get("selected_chokepoint")
        or payload.get("selected_country")
        or payload.get("selected_commodity")
        or "Global Supply Chain"
    )

    return {
        "status": "success",
        "agent_type": payload.get("agent_type", "full_supply_chain_briefing_agent"),
        "selected_target": selected_target,
        "output": {
            "executive_judgment": f"{selected_target} shows elevated supply chain risk due to converging geopolitical, logistics, market, and exposure signals.",
            "key_signals": [
                "Rising disruption indicators",
                "Elevated geopolitical pressure",
                "Potential route or supplier exposure",
                "Market sensitivity to chokepoint disruption"
            ],
            "risk_score": 78,
            "risk_level": "High",
            "main_drivers": [
                "Chokepoint concentration",
                "Geopolitical instability",
                "Limited substitution capacity",
                "Logistics pressure"
            ],
            "affected_sectors": [
                "Energy",
                "Shipping",
                "Manufacturing",
                "Defense",
                "Consumer goods"
            ],
            "forecast_horizon": payload.get("time_horizon", "30 days"),
            "confidence": "Medium-High",
            "recommended_actions": [
                "Monitor alternative routes",
                "Stress-test procurement timelines",
                "Review supplier concentration",
                "Run scenario simulation"
            ]
        }
    }
