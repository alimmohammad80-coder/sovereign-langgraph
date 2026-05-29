from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.alerts.alert_router import orchestrate_alert
from app.services.alerts.launch_context import build_launch_context

router = APIRouter(prefix="/api/alerts", tags=["Alert Orchestrator"])


# Temporary fallback data. Replace this later with Supabase/news/signals table.
RAW_ALERTS = [
    {
        "id": "taiwan-001",
        "title": "China carrier drills spark Taiwan warning over regional instability",
        "summary": "Chinese naval activity around Taiwan has increased alongside regional warnings.",
        "source": "Open Source Feed",
        "url": "",
        "score": 82,
        "created_at": "2026-05-29T00:00:00Z"
    },
    {
        "id": "hormuz-001",
        "title": "Shipping risk rises near the Strait of Hormuz amid regional tensions",
        "summary": "Energy and shipping routes face elevated exposure due to instability near Hormuz.",
        "source": "Open Source Feed",
        "url": "",
        "score": 76,
        "created_at": "2026-05-29T00:00:00Z"
    },
    {
        "id": "malacca-001",
        "title": "Southeast Asia debates tolling and strategic control around the Strait of Malacca",
        "summary": "Policy discussion around Malacca raises chokepoint and trade-route implications.",
        "source": "Open Source Feed",
        "url": "",
        "score": 60,
        "created_at": "2026-05-29T00:00:00Z"
    }
]


@router.get("/health")
def alerts_health():
    return {
        "status": "ok",
        "service": "alert_orchestrator",
        "purpose": "Detect, classify, prioritize, and route alerts to relevant modules."
    }


@router.get("/orchestrated")
def get_orchestrated_alerts(
    limit: int = Query(20, ge=1, le=100),
    domain: Optional[str] = None,
    severity: Optional[str] = None,
):
    alerts = [orchestrate_alert(a) for a in RAW_ALERTS]

    if domain:
        alerts = [a for a in alerts if domain in a.get("domains", [])]

    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]

    alerts = sorted(alerts, key=lambda x: x.get("risk_score", 0), reverse=True)

    return {
        "status": "success",
        "count": len(alerts[:limit]),
        "alerts": alerts[:limit],
        "message": "Alerts are routing objects, not reports."
    }


@router.get("/{alert_id}")
def get_alert_by_id(alert_id: str):
    for raw in RAW_ALERTS:
        if raw.get("id") == alert_id:
            return {
                "status": "success",
                "alert": orchestrate_alert(raw)
            }

    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/{alert_id}/launch-context")
def get_launch_context(alert_id: str, module: str):
    for raw in RAW_ALERTS:
        if raw.get("id") == alert_id:
            alert = orchestrate_alert(raw)
            return {
                "status": "success",
                "alert_id": alert_id,
                "module": module,
                "preloaded_context": build_launch_context(alert, module)
            }

    raise HTTPException(status_code=404, detail="Alert not found")


@router.get("/meta/domains")
def get_alert_domains():
    return {
        "status": "success",
        "domains": [
            "conflict",
            "supply_chain",
            "energy",
            "cyber",
            "geoeconomic",
            "political_risk",
            "geopolitical"
        ]
    }
