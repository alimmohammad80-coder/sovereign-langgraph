import os
from openai import OpenAI

from dotenv import load_dotenv
from app.services.intelligence_context_builder import build_supply_chain_context
from fastapi import APIRouter, HTTPException
from supabase import create_client

load_dotenv()

router = APIRouter(
    prefix="/api/supply-chain/geo",
    tags=["Supply Chain Geo"]
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is missing")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is missing")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@router.get("/nodes")
async def get_nodes():
    try:
        response = (
            supabase
            .table("sc_nodes")
            .select(
                "id,name,node_type,country,iso3,latitude,longitude,risk_score,severity,dominant_driver"
            )
            .execute()
        )

        features = []

        for row in response.data or []:
            if row.get("latitude") is None or row.get("longitude") is None:
                continue

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(row["longitude"]),
                        float(row["latitude"])
                    ]
                },
                "properties": {
                    "node_id": row["id"],
                    "name": row["name"],
                    "node_type": row["node_type"],
                    "country": row["country"],
                    "iso3": row["iso3"],
                    "risk_score": row["risk_score"],
                    "severity": row["severity"],
                    "dominant_driver": row["dominant_driver"]
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chokepoints")
async def get_chokepoints():
    try:
        response = (
            supabase
            .table("sc_chokepoints")
            .select("id,name,region,risk_score,severity,traffic_pct,closure_impact")
            .execute()
        )

        # Temporary bbox polygons from known chokepoint names.
        # Later we will read real PostGIS geometry as GeoJSON.
        bbox_lookup = {
            "Strait of Hormuz": [[55.8, 26.1], [56.7, 26.1], [56.7, 26.9], [55.8, 26.9], [55.8, 26.1]],
            "Taiwan Strait": [[119.0, 22.0], [122.5, 22.0], [122.5, 26.5], [119.0, 26.5], [119.0, 22.0]],
            "Strait of Malacca": [[99.0, 1.0], [104.5, 1.0], [104.5, 6.5], [99.0, 6.5], [99.0, 1.0]],
            "Suez Canal": [[32.0, 29.8], [32.8, 29.8], [32.8, 31.4], [32.0, 31.4], [32.0, 29.8]],
            "Bab el-Mandeb": [[42.5, 12.0], [44.0, 12.0], [44.0, 13.5], [42.5, 13.5], [42.5, 12.0]],
            "Panama Canal": [[-80.2, 8.7], [-79.3, 8.7], [-79.3, 9.5], [-80.2, 9.5], [-80.2, 8.7]],
        }

        features = []

        for row in response.data or []:
            coords = bbox_lookup.get(row["name"])
            if not coords:
                continue

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "chokepoint_id": row["id"],
                    "name": row["name"],
                    "region": row["region"],
                    "risk_score": row["risk_score"],
                    "severity": row["severity"],
                    "traffic_pct": row["traffic_pct"],
                    "closure_impact": row["closure_impact"]
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edges")
async def get_edges():
    try:
        response = (
            supabase
            .table("sc_edges")
            .select(
                "id,route_name,mode,is_chokepoint,avg_volume,risk_score,flow_share,from_node,to_node"
            )
            .execute()
        )

        nodes_response = (
            supabase
            .table("sc_nodes")
            .select("id,latitude,longitude,name")
            .execute()
        )

        nodes = {
            row["id"]: row
            for row in nodes_response.data or []
        }

        features = []

        for row in response.data or []:
            from_node = nodes.get(row["from_node"])
            to_node = nodes.get(row["to_node"])

            if not from_node or not to_node:
                continue

            if from_node.get("latitude") is None or from_node.get("longitude") is None:
                continue

            if to_node.get("latitude") is None or to_node.get("longitude") is None:
                continue

            coordinates = [
                [float(from_node["longitude"]), float(from_node["latitude"])],
                [float(to_node["longitude"]), float(to_node["latitude"])]
            ]

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "edge_id": row["id"],
                    "route_name": row["route_name"],
                    "mode": row["mode"],
                    "is_chokepoint": row["is_chokepoint"],
                    "avg_volume": row["avg_volume"],
                    "risk_score": row["risk_score"],
                    "flow_share": row["flow_share"],
                    "from_node_name": from_node["name"],
                    "to_node_name": to_node["name"]
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-flows")
async def get_trade_flows(limit: int = 50):
    try:
        response = (
            supabase
            .table("sc_raw_trade_flows")
            .select(
                "reporter_country,partner_country,reporter_iso3,partner_iso3,commodity_code,commodity_name,trade_flow,trade_value_usd,net_weight_kg,period"
            )
            .limit(limit)
            .execute()
        )

        return {
            "status": "success",
            "count": len(response.data or []),
            "data": response.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-exposure")
async def get_trade_exposure(limit: int = 50):
    try:
        response = (
            supabase
            .table("sc_trade_exposure_summary")
            .select(
                "commodity_code,commodity_name,reporter_country,partner_country,reporter_iso3,partner_iso3,trade_flow,total_trade_value_usd,total_weight_kg,period,exposure_score,exposure_level,decision_support"
            )
            .order("exposure_score", desc=True)
            .limit(limit)
            .execute()
        )

        return {
            "status": "success",
            "count": len(response.data or []),
            "data": response.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodity-risk/{commodity_code}")
async def get_commodity_risk(commodity_code: str):
    try:
        exposure = (
            supabase
            .table("sc_chokepoint_commodity_exposure")
            .select("*")
            .eq("commodity_code", commodity_code)
            .execute()
        )

        return {
            "commodity_code": commodity_code,
            "chokepoint_exposure": exposure.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/company-risk/{company_name}")
async def get_company_risk(company_name: str):
    try:
        company = (
            supabase
            .table("sc_company_exposure")
            .select("*")
            .ilike("company_name", company_name)
            .execute()
        )

        if not company.data:
            return {
                "status": "not_found",
                "company_name": company_name
            }

        results = []

        for item in company.data:
            exposure = (
                supabase
                .table("sc_chokepoint_commodity_exposure")
                .select("*")
                .eq("commodity_code", item["commodity_code"])
                .execute()
            )

            results.append({
                "company": item["company_name"],
                "commodity": item["commodity_name"],
                "supplier_country": item["supplier_country"],
                "dependency_pct": item["dependency_pct"],
                "criticality": item["criticality"],
                "chokepoint_exposure": exposure.data or []
            })

        return {
            "status": "success",
            "company_name": company_name,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supplier-alternatives/{commodity_code}")
async def get_supplier_alternatives(commodity_code: str):
    try:
        response = (
            supabase
            .table("sc_supplier_alternatives")
            .select("*")
            .eq("commodity_code", commodity_code)
            .order("resilience_score", desc=True)
            .execute()
        )

        return {
            "status": "success",
            "commodity_code": commodity_code,
            "alternatives": response.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/route-alternatives/{chokepoint_name}")
async def get_route_alternatives(chokepoint_name: str):
    try:
        response = (
            supabase
            .table("sc_route_alternatives")
            .select("*")
            .ilike("chokepoint_name", chokepoint_name)
            .order("risk_reduction_pct", desc=True)
            .execute()
        )

        return {
            "status": "success",
            "chokepoint": chokepoint_name,
            "alternatives": response.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scenario/{chokepoint_name}")
async def get_scenario(chokepoint_name: str):
    try:
        response = (
            supabase
            .table("sc_scenarios")
            .select("*")
            .ilike("chokepoint_name", chokepoint_name)
            .execute()
        )

        return {
            "status": "success",
            "scenario": response.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/commodities/{chokepoint_name}")
async def get_commodities(chokepoint_name: str):
    response = (
        supabase
        .table("sc_commodity_exposure")
        .select("*")
        .ilike("chokepoint_name", chokepoint_name)
        .execute()
    )

    return {
        "status": "success",
        "chokepoint": chokepoint_name,
        "commodities": response.data or []
    }

@router.get("/commodity-companies/{commodity}")
async def get_commodity_companies(commodity: str):
    response = (
        supabase
        .table("sc_commodity_company_exposure")
        .select("*")
        .ilike("commodity", commodity)
        .order("exposure_score", desc=True)
        .execute()
    )

    return {
        "status": "success",
        "commodity": commodity,
        "companies": response.data or []
    }

@router.get("/alternative-suppliers/{commodity}")
async def get_alternative_suppliers(commodity: str):
    response = (
        supabase
        .table("sc_alternative_suppliers")
        .select("*")
        .ilike("commodity", commodity)
        .order("geopolitical_risk_score", desc=False)
        .execute()
    )

    return {
        "status": "success",
        "commodity": commodity,
        "alternative_suppliers": response.data or []
    }

@router.get("/trade-flows/{chokepoint_name}")
async def get_trade_flows_by_chokepoint(chokepoint_name: str):
    response = (
        supabase
        .table("sc_trade_flows")
        .select("*")
        .contains("transit_chokepoints", [chokepoint_name])
        .order("annual_value_usd", desc=True)
        .execute()
    )

    return {
        "status": "success",
        "chokepoint": chokepoint_name,
        "trade_flows": response.data or []
    }

@router.get("/impact/{chokepoint_name}")
async def get_chokepoint_impact(chokepoint_name: str):

    scenario = (
        supabase
        .table("sc_scenarios")
        .select("*")
        .ilike("chokepoint_name", chokepoint_name)
        .execute()
    )

    commodities = (
        supabase
        .table("sc_commodity_exposure")
        .select("*")
        .ilike("chokepoint_name", chokepoint_name)
        .execute()
    )

    trade_flows = (
        supabase
        .table("sc_trade_flows")
        .select("*")
        .contains("transit_chokepoints", [chokepoint_name])
        .execute()
    )

    return {
        "status": "success",
        "chokepoint": chokepoint_name,
        "scenario": scenario.data or [],
        "commodities": commodities.data or [],
        "trade_flows": trade_flows.data or []
    }

@router.get("/exposure/{company_name}")
async def get_company_supply_chain_exposure(company_name: str):
    company_commodities = (
        supabase
        .table("sc_commodity_company_exposure")
        .select("*")
        .ilike("company_name", company_name)
        .execute()
    )

    company_ports = (
        supabase
        .table("sc_company_ports")
        .select("*")
        .ilike("company_name", company_name)
        .execute()
    )

    ports = company_ports.data or []
    chokepoints = []

    for port in ports:
        port_chokepoints = (
            supabase
            .table("sc_port_chokepoints")
            .select("*")
            .ilike("port_name", port["port_name"])
            .execute()
        )
        chokepoints.extend(port_chokepoints.data or [])

    commodity_names = [
        item["commodity"]
        for item in (company_commodities.data or [])
    ]

    alternative_suppliers = []

    for commodity in commodity_names:
        suppliers = (
            supabase
            .table("sc_alternative_suppliers")
            .select("*")
            .ilike("commodity", commodity)
            .order("geopolitical_risk_score", desc=False)
            .execute()
        )
        alternative_suppliers.extend(suppliers.data or [])

    return {
        "status": "success",
        "company": company_name,
        "commodities": company_commodities.data or [],
        "ports": ports,
        "chokepoints": chokepoints,
        "alternative_suppliers": alternative_suppliers
    }

@router.get("/briefing/{company_name}")
async def get_company_briefing(company_name: str):
    exposure = await get_company_supply_chain_exposure(company_name)

    commodities = exposure.get("commodities", [])
    ports = exposure.get("ports", [])
    chokepoints = exposure.get("chokepoints", [])
    alternatives = exposure.get("alternative_suppliers", [])

    max_score = max([c.get("exposure_score", 0) for c in commodities], default=50)

    if max_score >= 80:
        risk_level = "High"
    elif max_score >= 65:
        risk_level = "Elevated"
    else:
        risk_level = "Guarded"

    commodity_names = [c.get("commodity") for c in commodities]
    port_names = [p.get("port_name") for p in ports]
    chokepoint_names = [c.get("chokepoint_name") for c in chokepoints]
    supplier_names = [
        f"{s.get('supplier_company') or 'Supplier'} in {s.get('supplier_country')}"
        for s in alternatives
    ]

    return {
        "status": "success",
        "company": company_name,
        "exposure_score": max_score,
        "risk_level": risk_level,
        "bluf": f"{company_name} faces {risk_level.lower()} supply chain exposure driven by dependency on {', '.join(commodity_names) or 'critical inputs'} and transit risk through {', '.join(chokepoint_names) or 'key maritime chokepoints'}.",
        "critical_commodities": commodity_names,
        "critical_ports": port_names,
        "critical_chokepoints": chokepoint_names,
        "alternative_suppliers": supplier_names,
        "recommended_actions": [
            "Reduce single-route and single-supplier concentration.",
            "Increase inventory buffers for critical inputs.",
            "Monitor chokepoint disruption signals and export-control developments.",
            "Evaluate alternative suppliers and rerouting options."
        ],
        "raw_exposure": exposure
    }


@router.get("/company-profile/{company_name}")
async def get_company_profile(company_name: str):

    company_record = (
        supabase
        .table("sc_companies")
        .select("company_name,sector,headquarters_country,ticker,risk_score,severity,dominant_driver,baseline_risk_score,strategic_importance")
        .ilike("company_name", company_name)
        .limit(1)
        .execute()
    )

    exposure = await get_company_supply_chain_exposure(company_name)

    suppliers = (
        supabase
        .table("sc_company_suppliers")
        .select("*")
        .ilike("company_name", company_name)
        .execute()
    )

    markets = (
        supabase
        .table("sc_company_markets")
        .select("*")
        .ilike("company_name", company_name)
        .execute()
    )

    commodities = exposure.get("commodities", [])
    ports = exposure.get("ports", [])
    chokepoints = exposure.get("chokepoints", [])
    alternatives = exposure.get("alternative_suppliers", [])

    company_data = company_record.data[0] if company_record.data else {}

    exposure_score = (
        company_data.get("risk_score")
        or max([c.get("exposure_score", 0) for c in commodities], default=50)
    )

    risk_level = company_data.get("severity")

    if not risk_level:
        if exposure_score >= 85:
            risk_level = "Critical"
        elif exposure_score >= 75:
            risk_level = "High"
        elif exposure_score >= 60:
            risk_level = "Elevated"
        else:
            risk_level = "Guarded"

    return {
        "status": "success",
        "company": company_name,
        "company_record": company_data,
        "exposure_score": exposure_score,
        "risk_level": risk_level,
        "dominant_driver": company_data.get("dominant_driver"),
        "score_methodology": "Calculated from baseline company importance, linked port risk, supplier/commodity criticality, and dependency uplift.",
        "summary": {
            "commodities_count": len(commodities),
            "suppliers_count": len(suppliers.data or []),
            "ports_count": len(ports),
            "chokepoints_count": len(chokepoints),
            "markets_count": len(markets.data or [])
        },
        "commodities": commodities,
        "suppliers": suppliers.data or [],
        "ports": ports,
        "chokepoints": chokepoints,
        "alternative_suppliers": alternatives,
        "markets": markets.data or []
    }

@router.get("/scenario-impact/{chokepoint_name}")
async def get_scenario_impact(chokepoint_name: str):

    scenario = (
        supabase
        .table("sc_scenarios")
        .select("*")
        .ilike("chokepoint_name", chokepoint_name)
        .execute()
    )

    affected_ports = (
        supabase
        .table("sc_port_chokepoints")
        .select("*")
        .ilike("chokepoint_name", chokepoint_name)
        .execute()
    )

    port_names = [p.get("port_name") for p in (affected_ports.data or [])]

    affected_companies = []
    for port_name in port_names:
        company_ports = (
            supabase
            .table("sc_company_ports")
            .select("*")
            .ilike("port_name", port_name)
            .execute()
        )
        affected_companies.extend(company_ports.data or [])

    company_names = list({
        c.get("company_name")
        for c in affected_companies
        if c.get("company_name")
    })

    company_profiles = []
    affected_commodities = []
    alternative_suppliers = []

    for company_name in company_names:
        profile = await get_company_profile(company_name)
        company_profiles.append(profile)
        affected_commodities.extend(profile.get("commodities", []))
        alternative_suppliers.extend(profile.get("alternative_suppliers", []))

    alternative_routes = (
        supabase
        .table("sc_route_alternatives")
        .select("*")
        .ilike("chokepoint_name", chokepoint_name)
        .order("risk_reduction_pct", desc=True)
        .execute()
    )

    trade_flows = (
        supabase
        .table("sc_trade_flows")
        .select("*")
        .contains("transit_chokepoints", [chokepoint_name])
        .order("annual_value_usd", desc=True)
        .execute()
    )

    total_trade_value = sum([
        float(flow.get("annual_value_usd") or 0)
        for flow in (trade_flows.data or [])
    ])

    exposure_scores = [
        profile.get("exposure_score", 0)
        for profile in company_profiles
    ]

    scenario_score = max(exposure_scores, default=50)

    if scenario_score >= 80:
        risk_level = "High"
    elif scenario_score >= 65:
        risk_level = "Elevated"
    else:
        risk_level = "Guarded"

    return {
        "status": "success",
        "chokepoint": chokepoint_name,
        "risk_level": risk_level,
        "scenario_score": scenario_score,
        "summary": {
            "affected_ports_count": len(port_names),
            "affected_companies_count": len(company_names),
            "affected_trade_value_usd": total_trade_value,
            "affected_commodities_count": len(affected_commodities),
            "alternative_routes_count": len(alternative_routes.data or []),
            "alternative_suppliers_count": len(alternative_suppliers)
        },
        "scenario": scenario.data or [],
        "affected_ports": affected_ports.data or [],
        "affected_companies": affected_companies,
        "company_profiles": company_profiles,
        "affected_commodities": affected_commodities,
        "trade_flows": trade_flows.data or [],
        "alternative_routes": alternative_routes.data or [],
        "alternative_suppliers": alternative_suppliers,
        "recommended_actions": [
            "Identify companies with high dependency on affected ports and chokepoints.",
            "Prioritize alternative routing where risk reduction exceeds added cost.",
            "Increase inventory buffers for commodities tied to high-risk chokepoints.",
            "Review alternative suppliers in lower-risk jurisdictions.",
            "Monitor live disruption signals and update scenario assumptions daily."
        ]
    }

@router.get("/port-companies/{port_name}")
async def get_port_companies(port_name: str):
    response = (
        supabase
        .table("sc_company_ports")
        .select("*")
        .ilike("port_name", port_name)
        .execute()
    )

    return {
        "status": "success",
        "port": port_name,
        "companies": response.data or []
    }

@router.get("/live-disruptions")
async def get_live_disruptions(limit: int = 25):
    response = (
        supabase
        .table("sc_live_disruption_events")
        .select("*")
        .order("ingested_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "status": "success",
        "count": len(response.data or []),
        "events": response.data or []
    }

@router.get("/live-disruptions-clean")
async def get_live_disruptions_clean(limit: int = 25):
    response = (
        supabase
        .table("sc_live_disruption_events")
        .select("id,source,title,summary,url,event_type,matched_chokepoint,matched_port,matched_commodity,matched_company,severity_score,confidence_score,published_at,ingested_at")
        .order("ingested_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "status": "success",
        "count": len(response.data or []),
        "events": response.data or []
    }

@router.get("/pipeline/status")
async def get_supply_chain_pipeline_status():
    response = (
        supabase
        .table("sc_pipeline_status")
        .select("*")
        .order("updated_at", desc=True)
        .execute()
    )

    return {
        "status": "success",
        "pipelines": response.data or []
    }


@router.post("/pipeline/run-live-ingestion")
async def run_supply_chain_live_ingestion():
    from app.ingest.live_supply_chain_signals import run_live_supply_chain_ingestion
    from datetime import datetime, timezone

    try:
        result = run_live_supply_chain_ingestion() or {}

        supabase.table("sc_pipeline_status").upsert({
            "pipeline_name": "live_supply_chain_signals",
            "status": "completed",
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "records_processed": result.get("records_upserted") or result.get("records_inserted") or 0,
            "error_message": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="pipeline_name").execute()

        return {
            "status": "success",
            "pipeline": "live_supply_chain_signals",
            "result": result
        }

    except Exception as e:
        supabase.table("sc_pipeline_status").upsert({
            "pipeline_name": "live_supply_chain_signals",
            "status": "failed",
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "records_processed": 0,
            "error_message": str(e),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="pipeline_name").execute()

        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recalculate-scores")
async def recalculate_supply_chain_scores():
    events = (
        supabase
        .table("sc_live_disruption_events")
        .select("matched_chokepoint,severity_score")
        .not_.is_("matched_chokepoint", "null")
        .execute()
    )

    grouped = {}

    for event in events.data or []:
        chokepoint = event.get("matched_chokepoint")
        severity = float(event.get("severity_score") or 50)

        if chokepoint not in grouped:
            grouped[chokepoint] = []

        grouped[chokepoint].append(severity)

    updated = []

    for chokepoint, severities in grouped.items():
        avg_live_severity = sum(severities) / len(severities)

        existing = (
            supabase
            .table("sc_chokepoints")
            .select("risk_score")
            .ilike("name", chokepoint)
            .limit(1)
            .execute()
        )

        base_score = 50
        if existing.data:
            base_score = float(existing.data[0].get("risk_score") or 50)

        new_score = round((base_score * 0.7) + (avg_live_severity * 0.3), 1)

        if new_score >= 80:
            severity_label = "Critical"
        elif new_score >= 70:
            severity_label = "High"
        elif new_score >= 60:
            severity_label = "Elevated"
        else:
            severity_label = "Guarded"

        supabase.table("sc_chokepoints").update({
            "risk_score": new_score,
            "severity": severity_label
        }).ilike("name", chokepoint).execute()

        updated.append({
            "chokepoint": chokepoint,
            "base_score": base_score,
            "avg_live_severity": round(avg_live_severity, 1),
            "new_score": new_score,
            "severity": severity_label,
            "signals_used": len(severities)
        })

    return {
        "status": "success",
        "updated_count": len(updated),
        "updated": updated
    }

@router.post("/investigate")
async def investigate_supply_chain_entity(payload: dict):
    entity_type = payload.get("entity_type")
    entity_name = payload.get("entity_name")
    question = payload.get("question") or "Assess supply chain disruption risk and decision implications."

    if not entity_type or not entity_name:
        raise HTTPException(status_code=400, detail="entity_type and entity_name are required")

    context = {}

    if entity_type == "chokepoint":
        impact = await get_scenario_impact(entity_name)
        context = impact

    elif entity_type == "company":
        profile = await get_company_profile(entity_name)
        context = profile

    elif entity_type == "port":
        companies = (
            supabase
            .table("sc_company_ports")
            .select("*")
            .ilike("port_name", entity_name)
            .execute()
        )
        chokepoints = (
            supabase
            .table("sc_port_chokepoints")
            .select("*")
            .ilike("port_name", entity_name)
            .execute()
        )
        context = {
            "port": entity_name,
            "companies": companies.data or [],
            "chokepoints": chokepoints.data or []
        }

    elif entity_type == "commodity":
        companies = (
            supabase
            .table("sc_commodity_company_exposure")
            .select("*")
            .ilike("commodity", entity_name)
            .execute()
        )
        suppliers = (
            supabase
            .table("sc_alternative_suppliers")
            .select("*")
            .ilike("commodity", entity_name)
            .execute()
        )
        context = {
            "commodity": entity_name,
            "companies": companies.data or [],
            "alternative_suppliers": suppliers.data or []
        }

    else:
        raise HTTPException(status_code=400, detail="Unsupported entity_type")

    analysis = generate_supply_chain_gpt_analysis(
        entity_type=entity_type,
        entity_name=entity_name,
        question=question,
        context=context
    )

    return {
        "status": "success",
        "entity_type": entity_type,
        "entity_name": entity_name,
        "question": question,
        "context": context,
        "bluf": analysis.get("bluf"),
        "simulation": {
            "time_horizon": "30 days",
            "assessment": analysis.get("simulation_assessment"),
            "drivers": analysis.get("drivers", []),
            "forecast": analysis.get("forecast", {}),
            "recommended_actions": analysis.get("recommended_actions", []),
            "confidence": analysis.get("confidence")
        }
    }
@router.post("/recalculate-port-scores")
async def recalculate_port_scores():
    port_links = (
        supabase
        .table("sc_port_chokepoints")
        .select("*")
        .execute()
    )

    updated = []

    for link in port_links.data or []:
        port_name = link.get("port_name")
        chokepoint_name = link.get("chokepoint_name")
        dependency_pct = float(link.get("dependency_pct") or 50)

        chokepoint = (
            supabase
            .table("sc_chokepoints")
            .select("risk_score,severity")
            .ilike("name", chokepoint_name)
            .limit(1)
            .execute()
        )

        port = (
            supabase
            .table("sc_ports")
            .select("baseline_risk_score,risk_score")
            .ilike("port_name", port_name)
            .limit(1)
            .execute()
        )

        if not chokepoint.data or not port.data:
            continue

        chokepoint_score = float(chokepoint.data[0].get("risk_score") or 50)
        baseline_score = float(port.data[0].get("baseline_risk_score") or 50)

        dependency_weight = min(max(dependency_pct / 100, 0), 1)

        new_score = round(
            (baseline_score * 0.45)
            + (chokepoint_score * 0.40)
            + ((dependency_weight * 100) * 0.15),
            1
        )

        if new_score >= 80:
            severity = "Critical"
        elif new_score >= 70:
            severity = "High"
        elif new_score >= 60:
            severity = "Elevated"
        else:
            severity = "Guarded"

        dominant_driver = f"{chokepoint_name} dependency at {dependency_pct:.0f}%"

        (
            supabase
            .table("sc_ports")
            .update({
                "risk_score": new_score,
                "severity": severity,
                "dominant_driver": dominant_driver
            })
            .ilike("port_name", port_name)
            .execute()
        )

        updated.append({
            "port": port_name,
            "linked_chokepoint": chokepoint_name,
            "dependency_pct": dependency_pct,
            "chokepoint_score": chokepoint_score,
            "new_score": new_score,
            "severity": severity
        })

    return {
        "status": "success",
        "updated_count": len(updated),
        "updated": updated
    }


@router.post("/recalculate-company-scores")
async def recalculate_company_scores():
    companies = (
        supabase
        .table("sc_companies")
        .select("company_name,baseline_risk_score,strategic_importance")
        .execute()
    )

    updated = []

    for company in companies.data or []:
        company_name = company.get("company_name")
        baseline_score = float(
            company.get("baseline_risk_score")
            or company.get("strategic_importance")
            or 50
        )

        ports = (
            supabase
            .table("sc_company_ports")
            .select("port_name,dependency_pct")
            .ilike("company_name", company_name)
            .execute()
        )

        suppliers = (
            supabase
            .table("sc_company_suppliers")
            .select("supplier_name,commodity,dependency_pct,criticality")
            .ilike("company_name", company_name)
            .execute()
        )

        max_port_score = 50
        max_port_dependency = 0
        port_driver = None

        for port in ports.data or []:
            port_name = port.get("port_name")
            dependency_pct = float(port.get("dependency_pct") or 0)

            port_score_response = (
                supabase
                .table("sc_ports")
                .select("risk_score,severity,dominant_driver")
                .ilike("port_name", port_name)
                .limit(1)
                .execute()
            )

            if port_score_response.data:
                port_score = float(port_score_response.data[0].get("risk_score") or 50)
                if port_score > max_port_score:
                    max_port_score = port_score
                    max_port_dependency = dependency_pct
                    port_driver = f"{port_name} dependency at {dependency_pct:.0f}%"

        max_supplier_score = 50
        max_supplier_dependency = 0
        supplier_driver = None

        for supplier in suppliers.data or []:
            dependency_pct = float(supplier.get("dependency_pct") or 0)
            criticality = (supplier.get("criticality") or "").lower()

            if criticality == "critical":
                criticality_score = 90
            elif criticality == "high":
                criticality_score = 78
            elif criticality == "medium":
                criticality_score = 65
            else:
                criticality_score = 50

            if criticality_score > max_supplier_score:
                max_supplier_score = criticality_score
                max_supplier_dependency = dependency_pct
                supplier_driver = f"{supplier.get('commodity')} dependency at {dependency_pct:.0f}%"

        dependency_uplift = min(
            max(max_port_dependency, max_supplier_dependency) * 0.18,
            10
        )

        new_score = round(
            (baseline_score * 0.40)
            + (max_port_score * 0.35)
            + (max_supplier_score * 0.25)
            + dependency_uplift,
            1
        )

        new_score = min(new_score, 100)

        if new_score >= 85:
            severity = "Critical"
        elif new_score >= 75:
            severity = "High"
        elif new_score >= 60:
            severity = "Elevated"
        else:
            severity = "Guarded"

        dominant_driver = port_driver or supplier_driver or "Baseline company exposure"

        (
            supabase
            .table("sc_companies")
            .update({
                "risk_score": new_score,
                "severity": severity,
                "dominant_driver": dominant_driver
            })
            .ilike("company_name", company_name)
            .execute()
        )

        updated.append({
            "company": company_name,
            "new_score": new_score,
            "severity": severity,
            "dominant_driver": dominant_driver,
            "max_port_score": max_port_score,
            "max_supplier_score": max_supplier_score,
            "dependency_uplift": round(dependency_uplift, 1)
        })

    return {
        "status": "success",
        "updated_count": len(updated),
        "updated": updated
    }



def generate_supply_chain_gpt_analysis(entity_type, entity_name, question, context):
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "bluf": f"{entity_name} requires further assessment, but model analysis is unavailable because no NVIDIA_API_KEY or OPENAI_API_KEY is configured.",
            "simulation_assessment": "Model analysis unavailable.",
            "drivers": [],
            "forecast": {},
            "recommended_actions": []
        }

    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.getenv("NVIDIA_MODEL", "nvidia/llama-3_1-nemotron-ultra-253b-v1")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    prompt = f"""
You are Sovereign Intelligence AI's supply chain risk analyst.

Entity type: {entity_type}
Entity name: {entity_name}
User question: {question}

Use this backend context:
{context}

Produce a concise executive intelligence assessment.

Return only valid JSON with:
bluf: string
simulation_assessment: string
drivers: array of strings
forecast: object with 7_day, 30_day, 90_day
recommended_actions: array of strings
confidence: string
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
        )

        import json
        content = response.choices[0].message.content.strip()

        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        return json.loads(content)

    except Exception as e:
        return {
            "bluf": f"{entity_name} investigation completed using backend context, but model generation failed.",
            "simulation_assessment": str(e),
            "drivers": [],
            "forecast": {},
            "recommended_actions": [
                "Review linked ports, chokepoints, suppliers, and live signals.",
                "Refresh live ingestion and recalculate scores.",
                "Run the investigation again after model availability is restored."
            ],
            "confidence": "Low"
        }

@router.get("/port-dependencies/{port_name}")
async def get_port_dependencies(port_name: str):
    response = (
        supabase
        .table("sc_port_dependencies")
        .select("*")
        .ilike("port_name", port_name)
        .order("dependency_weight", desc=True)
        .execute()
    )

    return {
        "status": "success",
        "port": port_name,
        "count": len(response.data or []),
        "dependencies": response.data or []
    }

@router.get("/context/{entity_type}/{entity_name}")
async def get_supply_chain_context(entity_type: str, entity_name: str):
    context = build_supply_chain_context(
        supabase=supabase,
        entity_type=entity_type,
        entity_name=entity_name
    )

    return {
        "status": "success",
        "context": context
    }
