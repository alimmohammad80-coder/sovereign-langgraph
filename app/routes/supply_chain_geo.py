import os

from dotenv import load_dotenv
from app.services.intelligence_context_builder import build_supply_chain_context
from app.services.supply_chain_report_generator import (
    SupplyChainReportGenerationError,
    generate_professional_supply_chain_report,
)
from app.services.supply_chain_analysis_job_service import (
    SupplyChainAnalysisJobService,
)
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.services.supply_chain_risk_history import (
    build_risk_snapshot,
    calculate_confidence,
)
from app.services.maritime_risk_engine import (
    calculate_all_maritime_nodes,
)
from app.services.company_supply_chain_risk_engine import (
    calculate_all_companies,
)
from app.services.commodity_risk_engine import (
    calculate_all_commodities,
)
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
            .select("risk_score,baseline_risk_score")
            .ilike("name", chokepoint)
            .limit(1)
            .execute()
        )

        baseline_score = 50.0
        previous_score = None

        if existing.data:
            row = existing.data[0]

            baseline_score = float(
                row.get("baseline_risk_score")
                or row.get("risk_score")
                or 50
            )

            previous_score = float(
                row.get("risk_score")
                or baseline_score
            )

        signal_score = round(avg_live_severity, 1)

        dependency_score = baseline_score
        impact_score = baseline_score

        confidence_score = calculate_confidence(
            source_count=len(severities),
            fresh_source_count=len(severities),
            independent_source_count=min(len(severities), 5),
            relationship_coverage=70,
            source_reliability=70,
        )

        snapshot = build_risk_snapshot(
            entity_type="chokepoint",
            entity_name=chokepoint,
            baseline_risk_score=baseline_score,
            previous_risk_score=previous_score,
            signal_score=signal_score,
            dependency_score=dependency_score,
            impact_score=impact_score,
            confidence_score=confidence_score,
        )

        new_score = snapshot["current_risk_score"]

        if new_score >= 80:
            severity_label = "Critical"
        elif new_score >= 70:
            severity_label = "High"
        elif new_score >= 60:
            severity_label = "Elevated"
        else:
            severity_label = "Guarded"

        (
            supabase
            .table("sc_chokepoints")
            .update({
                "risk_score": new_score,
                "severity": severity_label,
            })
            .ilike("name", chokepoint)
            .execute()
        )

        supabase.table("sc_risk_history").insert(snapshot).execute()

        updated.append({
            "chokepoint": chokepoint,
            "baseline_score": baseline_score,
            "previous_score": previous_score,
            "signal_score": signal_score,
            "new_score": new_score,
            "score_delta": snapshot["score_delta"],
            "direction": snapshot["direction"],
            "confidence_score": snapshot["confidence_score"],
            "severity": severity_label,
            "signals_used": len(severities),
        })

    return {
        "status": "success",
        "updated_count": len(updated),
        "updated": updated,
    }

@router.post("/investigate")
async def investigate_supply_chain_entity(payload: dict):
    entity_type = payload.get("entity_type")
    entity_name = payload.get("entity_name")
    question = payload.get("question") or (
        "Produce a current, decision-relevant supply-chain intelligence assessment."
    )

    if not entity_type or not entity_name:
        raise HTTPException(status_code=400, detail="entity_type and entity_name are required")

    if entity_type == "chokepoint":
        context = await get_scenario_impact(entity_name)
    elif entity_type == "company":
        context = await get_company_profile(entity_name)
    elif entity_type == "port":
        context = build_supply_chain_context(
            supabase=supabase,
            entity_type="port",
            entity_name=entity_name,
        )
    elif entity_type == "commodity":
        companies = (
            supabase.table("sc_commodity_company_exposure")
            .select("*")
            .ilike("commodity", entity_name)
            .execute()
        )
        suppliers = (
            supabase.table("sc_alternative_suppliers")
            .select("*")
            .ilike("commodity", entity_name)
            .execute()
        )
        context = {
            "commodity": entity_name,
            "companies": companies.data or [],
            "alternative_suppliers": suppliers.data or [],
        }
    elif entity_type == "country":
        ports = (
            supabase.table("sc_master_ports")
            .select("*")
            .ilike("country", entity_name)
            .execute()
        )
        companies = (
            supabase.table("sc_companies")
            .select("*")
            .ilike("headquarters_country", entity_name)
            .execute()
        )
        context = {
            "country": entity_name,
            "ports": ports.data or [],
            "companies": companies.data or [],
        }
    elif entity_type in {"corridor", "shipping_corridor"}:
        corridor = (
            supabase.table("sc_shipping_corridors")
            .select("*")
            .ilike("corridor_name", entity_name)
            .limit(1)
            .execute()
        )
        context = {
            "entity_type": "shipping_corridor",
            "entity_name": entity_name,
            "profile": corridor.data[0] if corridor.data else None,
        }
        entity_type = "shipping_corridor"
    else:
        raise HTTPException(status_code=400, detail="Unsupported entity_type")

    try:
        analysis = generate_supply_chain_gpt_analysis(
            entity_type=entity_type,
            entity_name=entity_name,
            question=question,
            context=context,
        )
    except SupplyChainReportGenerationError as model_error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "REPORT_QUALITY_GATE_FAILED",
                "message": (
                    "A publication-quality intelligence report could not be generated. "
                    "No fallback report was published."
                ),
            },
        ) from model_error

    return {
        "status": "success",
        "entity_type": entity_type,
        "entity_name": entity_name,
        "question": question,
        "context": context,
        "bluf": analysis.get("bluf"),
        "report": analysis,
        "simulation": {
            "time_horizon": "30 days",
            "complete_analysis": analysis.get("complete_analysis"),
            "strategic_assessment": analysis.get("strategic_assessment"),
            "assessment": analysis.get("simulation_assessment"),
            "key_judgments": analysis.get("key_judgments", []),
            "drivers": analysis.get("drivers", []),
            "forecast": analysis.get("forecast", {}),
            "early_warning_indicators": analysis.get("early_warning_indicators", []),
            "recommended_actions": analysis.get("recommended_actions", []),
            "confidence": analysis.get("confidence"),
            "confidence_rationale": analysis.get("confidence_rationale"),
            "intelligence_gaps": analysis.get("intelligence_gaps", []),
            "sources": analysis.get("sources", []),
            "analysis_word_count": analysis.get("analysis_word_count"),
            "generated_at": analysis.get("generated_at"),
            "generation_status": analysis.get("generation_status"),
        },
    }

@router.post("/recalculate-port-scores")
async def recalculate_port_scores():
    """
    Recalculate risk across the global master-port registry.

    Authoritative tables:
    - sc_master_ports
    - sc_port_dependencies
    - sc_maritime_nodes
    - sc_live_disruption_events
    - sc_risk_history

    Port baseline risk remains structural.
    Current risk incorporates chokepoint dependency and live port signals.
    """

    ports_response = (
        supabase
        .table("sc_master_ports")
        .select(
            "port_name,country,region,baseline_risk_score,"
            "risk_score,strategic_importance,severity"
        )
        .execute()
    )

    dependencies_response = (
        supabase
        .table("sc_port_dependencies")
        .select(
            "port_name,dependency_type,dependency_name,"
            "dependency_weight,category,notes"
        )
        .execute()
    )

    maritime_nodes_response = (
        supabase
        .table("sc_maritime_nodes")
        .select(
            "name,canonical_name,node_type,region,"
            "risk_score,baseline_risk_score,severity,"
            "strategic_importance"
        )
        .eq("is_active", True)
        .execute()
    )

    live_events_response = (
        supabase
        .table("sc_live_disruption_events")
        .select(
            "matched_port,severity_score,confidence_score,"
            "published_at,source"
        )
        .not_.is_("matched_port", "null")
        .execute()
    )

    ports = ports_response.data or []
    dependencies = dependencies_response.data or []
    maritime_nodes = maritime_nodes_response.data or []
    live_events = live_events_response.data or []

    maritime_node_lookup = {}

    for row in maritime_nodes:
        name = str(row.get("name") or "").strip()
        canonical_name = str(
            row.get("canonical_name") or name
        ).strip()

        if name:
            maritime_node_lookup[name.lower()] = row

        if canonical_name:
            maritime_node_lookup[canonical_name.lower()] = row

    dependency_lookup = {}

    for row in dependencies:
        port_name = row.get("port_name")
        if not port_name:
            continue

        dependency_lookup.setdefault(
            str(port_name).strip().lower(),
            []
        ).append(row)

    live_event_lookup = {}

    for event in live_events:
        port_name = event.get("matched_port")
        if not port_name:
            continue

        live_event_lookup.setdefault(
            str(port_name).strip().lower(),
            []
        ).append(event)

    updated = []

    for port in ports:
        port_name = port.get("port_name")

        if not port_name:
            continue

        port_key = str(port_name).strip().lower()

        baseline_score = float(
            port.get("baseline_risk_score")
            or port.get("risk_score")
            or 50
        )

        previous_score = float(
            port.get("risk_score")
            or baseline_score
        )

        port_dependencies = dependency_lookup.get(port_key, [])

        weighted_dependency_scores = []
        dominant_driver = None
        dominant_driver_value = -1.0
        matched_dependencies = []

        for dependency in port_dependencies:
            dependency_type = str(
                dependency.get("dependency_type") or ""
            ).strip().lower()

            dependency_name = str(
                dependency.get("dependency_name") or ""
            ).strip()

            dependency_weight_pct = float(
                dependency.get("dependency_weight") or 0
            )

            if (
                dependency_type == "chokepoint"
                and dependency_name
            ):
                maritime_node = maritime_node_lookup.get(
                    dependency_name.lower()
                )

                if not maritime_node:
                    continue

                node_score = maritime_node.get("risk_score")

                if node_score is None:
                    node_score = maritime_node.get(
                        "baseline_risk_score"
                    )

                # Do not invent a maritime risk score.
                # If the node exists but is not yet scored,
                # retain the relationship but exclude it from
                # numerical propagation.
                if node_score is None:
                    matched_dependencies.append(
                        dependency_name
                    )
                    continue

                chokepoint_score = float(node_score)

                normalized_weight = min(
                    max(dependency_weight_pct / 100.0, 0.0),
                    1.0,
                )

                weighted_score = (
                    chokepoint_score * normalized_weight
                )

                weighted_dependency_scores.append({
                    "dependency_name": dependency_name,
                    "dependency_weight": dependency_weight_pct,
                    "chokepoint_score": chokepoint_score,
                    "weighted_score": weighted_score,
                })

                driver_strength = (
                    chokepoint_score * normalized_weight
                )

                if driver_strength > dominant_driver_value:
                    dominant_driver_value = driver_strength
                    dominant_driver = (
                        f"{dependency_name} dependency at "
                        f"{dependency_weight_pct:.0f}%"
                    )

                matched_dependencies.append(
                    dependency_name
                )

        if weighted_dependency_scores:
            total_weight = sum(
                min(
                    max(
                        item["dependency_weight"] / 100.0,
                        0.0,
                    ),
                    1.0,
                )
                for item in weighted_dependency_scores
            )

            if total_weight > 0:
                dependency_risk_score = sum(
                    item["chokepoint_score"]
                    * min(
                        max(
                            item["dependency_weight"] / 100.0,
                            0.0,
                        ),
                        1.0,
                    )
                    for item in weighted_dependency_scores
                ) / total_weight
            else:
                dependency_risk_score = baseline_score

            dependency_intensity = min(
                max(
                    max(
                        item["dependency_weight"]
                        for item in weighted_dependency_scores
                    ),
                    0,
                ),
                100,
            )
        else:
            dependency_risk_score = baseline_score
            dependency_intensity = 0.0

        port_events = live_event_lookup.get(port_key, [])

        if port_events:
            event_severities = [
                float(event.get("severity_score") or 50)
                for event in port_events
            ]

            signal_score = round(
                sum(event_severities) / len(event_severities),
                1,
            )

            event_confidences = [
                float(event.get("confidence_score") or 60)
                for event in port_events
            ]

            avg_event_confidence = round(
                sum(event_confidences)
                / len(event_confidences),
                1,
            )

            distinct_sources = len({
                str(event.get("source") or "").strip().lower()
                for event in port_events
                if event.get("source")
            })
        else:
            signal_score = baseline_score
            avg_event_confidence = 60.0
            distinct_sources = 0

        # Dependency risk combines the risk of connected chokepoints
        # with how dependent the port is on those routes.
        dependency_score = round(
            (
                dependency_risk_score * 0.75
                + dependency_intensity * 0.25
            ),
            1,
        )

        # First-generation impact proxy.
        # Strategic importance is used until throughput, trade-value,
        # commodity concentration, and substitution data are integrated.
        impact_score = float(
            port.get("strategic_importance")
            or baseline_score
        )

        relationship_coverage = min(
            100.0,
            40.0 + len(matched_dependencies) * 20.0
        )

        confidence_score = calculate_confidence(
            source_count=len(port_events),
            fresh_source_count=len(port_events),
            independent_source_count=min(
                distinct_sources,
                5,
            ),
            relationship_coverage=relationship_coverage,
            source_reliability=avg_event_confidence,
        )

        # If there are no live port events, preserve some baseline
        # evidence confidence from structural and dependency coverage.
        if not port_events:
            confidence_score = calculate_confidence(
                source_count=len(matched_dependencies),
                fresh_source_count=0,
                independent_source_count=min(
                    len(matched_dependencies),
                    5,
                ),
                relationship_coverage=relationship_coverage,
                source_reliability=70,
            )

        snapshot = build_risk_snapshot(
            entity_type="port",
            entity_name=port_name,
            baseline_risk_score=baseline_score,
            previous_risk_score=previous_score,
            signal_score=signal_score,
            dependency_score=dependency_score,
            impact_score=impact_score,
            confidence_score=confidence_score,
        )

        new_score = snapshot["current_risk_score"]

        if new_score >= 80:
            severity = "Critical"
        elif new_score >= 70:
            severity = "High"
        elif new_score >= 60:
            severity = "Elevated"
        elif new_score >= 40:
            severity = "Guarded"
        else:
            severity = "Low"

        if not dominant_driver:
            if port_events:
                dominant_driver = (
                    f"{len(port_events)} live disruption "
                    f"signal(s)"
                )
            else:
                dominant_driver = "Structural port exposure"

        (
            supabase
            .table("sc_master_ports")
            .update({
                "risk_score": new_score,
                "severity": severity,
                "dominant_driver": dominant_driver,
            })
            .ilike("port_name", port_name)
            .execute()
        )

        supabase.table("sc_risk_history").insert(
            snapshot
        ).execute()

        updated.append({
            "port": port_name,
            "baseline_score": baseline_score,
            "previous_score": previous_score,
            "new_score": new_score,
            "score_delta": snapshot["score_delta"],
            "direction": snapshot["direction"],
            "confidence_score": snapshot[
                "confidence_score"
            ],
            "signal_score": signal_score,
            "dependency_score": dependency_score,
            "impact_score": impact_score,
            "severity": severity,
            "dominant_driver": dominant_driver,
            "matched_chokepoints": matched_dependencies,
            "live_signals_used": len(port_events),
        })

    return {
        "status": "success",
        "registry": "sc_master_ports",
        "ports_assessed": len(ports),
        "updated_count": len(updated),
        "updated": updated,
    }


@router.post("/recalculate-company-scores")
async def recalculate_company_scores():
    companies = (
        supabase
        .table("sc_companies")
        .select("*")
        .execute()
    )

    master_ports = (
        supabase
        .table("sc_master_ports")
        .select("port_name,risk_score,severity,dominant_driver")
        .execute()
    )

    commodities_master = (
        supabase
        .table("sc_commodities")
        .select(
            "commodity_name,risk_score,severity,"
            "confidence_score,dominant_driver"
        )
        .execute()
    )

    company_ports = (
        supabase
        .table("sc_company_ports")
        .select("*")
        .execute()
    )

    company_suppliers = (
        supabase
        .table("sc_company_suppliers")
        .select("*")
        .execute()
    )

    commodity_exposures = (
        supabase
        .table("sc_commodity_company_exposure")
        .select("*")
        .execute()
    )

    company_markets = (
        supabase
        .table("sc_company_markets")
        .select("*")
        .execute()
    )

    live_events = (
        supabase
        .table("sc_live_disruption_events")
        .select(
            "matched_company,severity_score,"
            "confidence_score,source,published_at"
        )
        .not_.is_("matched_company", "null")
        .execute()
    )

    assessments = calculate_all_companies(
        companies=companies.data or [],
        master_ports=master_ports.data or [],
        commodities_master=commodities_master.data or [],
        company_ports=company_ports.data or [],
        company_suppliers=company_suppliers.data or [],
        commodity_exposures=commodity_exposures.data or [],
        company_markets=company_markets.data or [],
        live_events=live_events.data or [],
    )

    updated = []

    for assessment in assessments:
        (
            supabase
            .table("sc_companies")
            .update({
                "risk_score": assessment["new_score"],
                "severity": assessment["severity"],
                "dominant_driver": assessment["dominant_driver"],
                "port_exposure_score": assessment[
                    "port_exposure_score"
                ],
                "supplier_exposure_score": assessment[
                    "supplier_exposure_score"
                ],
                "commodity_exposure_score": assessment[
                    "commodity_exposure_score"
                ],
                "market_exposure_score": assessment[
                    "market_exposure_score"
                ],
                "live_signal_score": assessment[
                    "live_signal_score"
                ],
                "confidence_score": assessment[
                    "confidence_score"
                ],
                "score_direction": assessment["direction"],
                "model_version": assessment["model_version"],
                "last_calculated_at": assessment[
                    "last_calculated_at"
                ],
            })
            .ilike("company_name", assessment["company"])
            .execute()
        )

        supabase.table("sc_risk_history").insert(
            assessment["snapshot"]
        ).execute()

        updated.append({
            key: value
            for key, value in assessment.items()
            if key != "snapshot"
        })

    return {
        "status": "success",
        "model_version": "sc-company-risk-v1",
        "companies_assessed": len(assessments),
        "updated_count": len(updated),
        "updated": updated,
    }



@router.post("/recalculate-commodity-scores")
async def recalculate_commodity_scores():
    commodities_response = (
        supabase
        .table("sc_commodities")
        .select("*")
        .execute()
    )

    quantitative_exposure_response = (
        supabase
        .table("sc_commodity_exposure")
        .select("*")
        .execute()
    )

    structural_exposure_response = (
        supabase
        .table("sc_chokepoint_commodity_exposure")
        .select("*")
        .execute()
    )

    alternative_suppliers_response = (
        supabase
        .table("sc_alternative_suppliers")
        .select("*")
        .execute()
    )

    live_events_response = (
        supabase
        .table("sc_live_disruption_events")
        .select(
            "matched_commodity,severity_score,"
            "confidence_score,source,published_at"
        )
        .not_.is_("matched_commodity", "null")
        .execute()
    )

    maritime_nodes_response = (
        supabase
        .table("sc_maritime_nodes")
        .select(
            "name,canonical_name,node_type,region,"
            "baseline_risk_score,risk_score,severity,"
            "confidence_score,score_direction"
        )
        .execute()
    )

    assessments = calculate_all_commodities(
        commodities=commodities_response.data or [],
        quantitative_exposures=(
            quantitative_exposure_response.data or []
        ),
        structural_exposures=(
            structural_exposure_response.data or []
        ),
        alternatives=(
            alternative_suppliers_response.data or []
        ),
        live_events=(
            live_events_response.data or []
        ),
        maritime_nodes=(
            maritime_nodes_response.data or []
        ),
    )

    updated = []

    for assessment in assessments:
        (
            supabase
            .table("sc_commodities")
            .update({
                "risk_score": assessment["new_score"],
                "severity": assessment["severity"],
                "chokepoint_exposure_score": assessment[
                    "chokepoint_exposure_score"
                ],
                "concentration_score": assessment[
                    "concentration_score"
                ],
                "alternative_supply_score": assessment[
                    "alternative_supply_score"
                ],
                "live_signal_score": assessment[
                    "live_signal_score"
                ],
                "confidence_score": assessment[
                    "confidence_score"
                ],
                "score_direction": assessment[
                    "direction"
                ],
                "dominant_driver": assessment[
                    "dominant_driver"
                ],
                "model_version": assessment[
                    "model_version"
                ],
                "last_calculated_at": assessment[
                    "last_calculated_at"
                ],
            })
            .ilike(
                "commodity_name",
                assessment["commodity"],
            )
            .execute()
        )

        supabase.table("sc_risk_history").insert(
            assessment["snapshot"]
        ).execute()

        updated.append({
            key: value
            for key, value in assessment.items()
            if key != "snapshot"
        })

    return {
        "status": "success",
        "model_version": "sc-commodity-risk-v1",
        "commodities_assessed": len(assessments),
        "updated_count": len(updated),
        "updated": updated,
    }




def generate_supply_chain_gpt_analysis(
    entity_type: str,
    entity_name: str,
    question: str,
    context: dict,
):
    """Generate a validated, publication-quality intelligence report."""
    return generate_professional_supply_chain_report(
        entity_type=entity_type,
        entity_name=entity_name,
        question=question,
        context=context,
    )


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

@router.get("/shipping-corridors")
async def get_shipping_corridors():
    response = (
        supabase
        .table("sc_shipping_corridors")
        .select("*")
        .order("risk_score", desc=True)
        .execute()
    )

    return {
        "status": "success",
        "count": len(response.data or []),
        "corridors": response.data or []
    }


@router.get("/shipping-corridors/{corridor_name}")
async def get_shipping_corridor(corridor_name: str):
    response = (
        supabase
        .table("sc_shipping_corridors")
        .select("*")
        .ilike("corridor_name", corridor_name)
        .limit(1)
        .execute()
    )

    return {
        "status": "success",
        "corridor": response.data[0] if response.data else None
    }


@router.post("/run-investigation")
async def run_supply_chain_investigation(payload: dict):
    try:
        selected_entities = payload.get("selected_entities") or {}
        scenario_question = payload.get("scenario_question") or "Assess selected supply chain dependencies, shipping corridor exposure, live signals, and 30-day disruption impact."

        def default_next_questions(question: str):
            return [
                {
                    "module": "strategic_early_warning",
                    "label": "Strategic Early Warning",
                    "question": f"What early warning indicators would signal escalation from this supply chain disruption: {question}?",
                    "route": "/strategic-early-warning",
                    "auto_run": True
                },
                {
                    "module": "financial_risk",
                    "label": "Stocks / Portfolio Risk",
                    "question": f"What are the likely equity, sector, commodity price, and portfolio risk impacts of this supply chain disruption: {question}?",
                    "route": "/financial-risk",
                    "auto_run": True
                },
                {
                    "module": "conflict_intelligence",
                    "label": "Conflict Escalation",
                    "question": f"What conflict escalation pathways could emerge from this supply chain disruption: {question}?",
                    "route": "/conflict-intelligence",
                    "auto_run": True
                }
            ]

        contexts = {
            "ports": [],
            "companies": [],
            "chokepoints": [],
            "commodities": [],
            "countries": [],
            "shipping_corridors": [],
            "live_signals": [],
            "live_signal_summary": {}
        }

        selected_count = sum(
            len(v) for v in selected_entities.values()
            if isinstance(v, list)
        )

        if selected_count == 0:
            raise HTTPException(status_code=400, detail="At least one selected entity is required")

        for port in selected_entities.get("ports", []):
            contexts["ports"].append(build_supply_chain_context(supabase, "port", port))

        for company in selected_entities.get("companies", []):
            contexts["companies"].append(build_supply_chain_context(supabase, "company", company))

        for chokepoint in selected_entities.get("chokepoints", []):
            contexts["chokepoints"].append(build_supply_chain_context(supabase, "chokepoint", chokepoint))

        for commodity in selected_entities.get("commodities", []):
            commodity_context = (
                supabase.table("sc_commodity_company_exposure")
                .select("*")
                .ilike("commodity", commodity)
                .execute()
            )

            alternative_suppliers = (
                supabase.table("sc_alternative_suppliers")
                .select("*")
                .ilike("commodity", commodity)
                .execute()
            )

            contexts["commodities"].append({
                "entity_type": "commodity",
                "entity_name": commodity,
                "company_exposure": commodity_context.data or [],
                "alternative_suppliers": alternative_suppliers.data or []
            })

        for country in selected_entities.get("countries", []):
            ports = (
                supabase.table("sc_master_ports")
                .select("*")
                .ilike("country", country)
                .execute()
            )

            companies = (
                supabase.table("sc_companies")
                .select("*")
                .ilike("headquarters_country", country)
                .execute()
            )

            contexts["countries"].append({
                "entity_type": "country",
                "entity_name": country,
                "ports": ports.data or [],
                "companies": companies.data or []
            })

        for corridor in selected_entities.get("shipping_corridors", []):
            corridor_response = (
                supabase.table("sc_shipping_corridors")
                .select("*")
                .ilike("corridor_name", corridor)
                .limit(1)
                .execute()
            )

            contexts["shipping_corridors"].append({
                "entity_type": "shipping_corridor",
                "entity_name": corridor,
                "profile": corridor_response.data[0] if corridor_response.data else None
            })

        selected_names = []
        for values in selected_entities.values():
            if isinstance(values, list):
                selected_names.extend(values)

        live_response = (
            supabase.table("sc_live_disruption_events")
            .select("source,title,summary,url,event_type,matched_port,matched_chokepoint,matched_commodity,matched_company,severity_score,confidence_score,published_at,ingested_at")
            .order("ingested_at", desc=True)
            .limit(75)
            .execute()
        )

        matched_live_signals = []
        for signal in live_response.data or []:
            searchable = " ".join([
                str(signal.get("title") or ""),
                str(signal.get("summary") or ""),
                str(signal.get("matched_port") or ""),
                str(signal.get("matched_chokepoint") or ""),
                str(signal.get("matched_commodity") or ""),
                str(signal.get("matched_company") or "")
            ]).lower()

            for name in selected_names:
                if name and name.lower() in searchable:
                    matched_live_signals.append(signal)
                    break

        contexts["live_signals"] = matched_live_signals[:15]
        contexts["live_signal_summary"] = {
            "matched_count": len(matched_live_signals),
            "latest_ingested_at": matched_live_signals[0].get("ingested_at") if matched_live_signals else None
        }

        selected_pairs = [
            (group, str(name))
            for group, names in selected_entities.items()
            if isinstance(names, list)
            for name in names
            if name
        ]
        group_to_type = {
            "ports": "port",
            "companies": "company",
            "chokepoints": "chokepoint",
            "commodities": "commodity",
            "countries": "country",
            "shipping_corridors": "shipping_corridor",
        }
        if len(selected_pairs) == 1:
            selected_group, selected_name = selected_pairs[0]
            report_entity_type = group_to_type.get(selected_group, selected_group)
            report_entity_name = selected_name
        else:
            report_entity_type = "multi_entity_investigation"
            report_entity_name = ", ".join(name for _, name in selected_pairs[:5])

        try:
            analysis = generate_supply_chain_gpt_analysis(
                entity_type=report_entity_type,
                entity_name=report_entity_name,
                question=scenario_question,
                context=contexts,
            )
        except SupplyChainReportGenerationError as model_error:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "REPORT_QUALITY_GATE_FAILED",
                    "message": (
                        "A publication-quality intelligence report could not be generated. "
                        "No fallback report was published."
                    ),
                },
            ) from model_error

        if not isinstance(analysis, dict):
            analysis = {}

        if not analysis.get("next_simulation_questions"):
            analysis["next_simulation_questions"] = default_next_questions(scenario_question)

        return {
            "status": "success",
            "scenario_question": scenario_question,
            "selected_entities": selected_entities,
            "context": contexts,
            "bluf": analysis.get("bluf"),
            "report": analysis,
            "simulation": {
                "time_horizon": "30 days",
                "complete_analysis": analysis.get("complete_analysis"),
                "strategic_assessment": analysis.get("strategic_assessment"),
                "assessment": analysis.get("simulation_assessment"),
                "key_judgments": analysis.get("key_judgments", []),
                "goods_impact": analysis.get("goods_impact", []),
                "commodity_impact": analysis.get("commodity_impact", []),
                "company_impact": analysis.get("company_impact", []),
                "market_impact": analysis.get("market_impact"),
                "supply_chain_impact": analysis.get("supply_chain_impact"),
                "second_order_effects": analysis.get("second_order_effects", []),
                "drivers": analysis.get("drivers", []),
                "forecast": analysis.get("forecast", {}),
                "early_warning_indicators": analysis.get("early_warning_indicators", []),
                "recommended_actions": analysis.get("recommended_actions", []),
                "next_simulation_questions": analysis.get("next_simulation_questions", []),
                "confidence": analysis.get("confidence"),
                "confidence_rationale": analysis.get("confidence_rationale"),
                "intelligence_gaps": analysis.get("intelligence_gaps", []),
                "sources": analysis.get("sources", []),
                "analysis_word_count": analysis.get("analysis_word_count"),
                "generated_at": analysis.get("generated_at"),
                "generation_status": analysis.get("generation_status"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
            "message": "run-investigation failed before model analysis"
        }


def _resolve_supply_chain_report_subject(payload: dict) -> tuple[str, str]:
    selected_entities = payload.get("selected_entities") or {}
    selected_pairs = [
        (group, str(name))
        for group, names in selected_entities.items()
        if isinstance(names, list)
        for name in names
        if name
    ]
    if not selected_pairs:
        raise HTTPException(
            status_code=400,
            detail="At least one selected entity is required",
        )

    group_to_type = {
        "ports": "port",
        "companies": "company",
        "chokepoints": "chokepoint",
        "commodities": "commodity",
        "countries": "country",
        "shipping_corridors": "shipping_corridor",
    }
    if len(selected_pairs) == 1:
        group, name = selected_pairs[0]
        return group_to_type.get(group, group), name

    return (
        "multi_entity_investigation",
        ", ".join(name for _, name in selected_pairs[:5]),
    )


async def _run_supply_chain_analysis_job(job_id: str) -> None:
    service = SupplyChainAnalysisJobService()
    job = service.get(job_id)
    if not job:
        return

    service.mark_processing(job_id)
    try:
        result = await run_supply_chain_investigation(
            job.get("request_json") or {}
        )
        if not isinstance(result, dict) or result.get("status") != "success":
            raise RuntimeError("Supply-chain report generation did not complete.")
        service.complete(job_id, result)
    except Exception as exc:
        service.fail(job_id, exc)


@router.post("/analysis-jobs")
def create_supply_chain_analysis_job(
    payload: dict,
    background_tasks: BackgroundTasks,
):
    entity_type, entity_name = _resolve_supply_chain_report_subject(payload)
    service = SupplyChainAnalysisJobService()
    job = service.create(
        entity_type=entity_type,
        entity_name=entity_name,
        request_json=payload,
    )
    background_tasks.add_task(
        _run_supply_chain_analysis_job,
        str(job["id"]),
    )
    return {
        "status": "success",
        "data": {
            "analysis_id": str(job["id"]),
            "entity_type": entity_type,
            "entity_name": entity_name,
            "status": "queued",
        },
    }


@router.get("/analysis-jobs/{analysis_id}")
def get_supply_chain_analysis_job(analysis_id: str):
    job = SupplyChainAnalysisJobService().get(analysis_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Supply-chain analysis job not found.",
        )

    response = {
        "analysis_id": str(job["id"]),
        "entity_type": job["entity_type"],
        "entity_name": job["entity_name"],
        "status": job["status"],
        "provider": job.get("provider"),
        "model": job.get("model"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
    }
    if job["status"] == "completed":
        response["result"] = job.get("result")
        response["qa"] = job.get("qa")
    elif job["status"] == "failed":
        response["error"] = job.get("error_message")

    return {
        "status": "success",
        "data": response,
    }


@router.get("/toolbox/{category}")
async def get_supply_chain_toolbox(category: str):
    category = category.lower()

    if category == "ports":
        r = supabase.table("sc_master_ports").select("port_name,country,region,risk_score,severity,strategic_importance").order("strategic_importance", desc=True).execute()
        return {"status": "success", "category": category, "count": len(r.data or []), "items": r.data or []}

    if category == "chokepoints":
        r = supabase.table("sc_chokepoints").select("name,region,risk_score,severity,traffic_pct").order("risk_score", desc=True).execute()
        return {"status": "success", "category": category, "count": len(r.data or []), "items": r.data or []}

    if category == "countries":
        ports = supabase.table("sc_master_ports").select("country,iso3,region").execute()
        seen = {}
        for row in ports.data or []:
            name = row.get("country")
            if name and name not in seen:
                seen[name] = row
        items = sorted(seen.values(), key=lambda x: x.get("country") or "")
        return {"status": "success", "category": category, "count": len(items), "items": items}

    if category == "commodities":
        r = supabase.table("sc_commodity_company_exposure").select("commodity,sector,exposure_score").execute()
        seen = {}
        for row in r.data or []:
            name = row.get("commodity")
            if name and name not in seen:
                seen[name] = row
        items = sorted(seen.values(), key=lambda x: x.get("commodity") or "")
        return {"status": "success", "category": category, "count": len(items), "items": items}

    if category == "companies":
        r = supabase.table("sc_companies").select("company_name,sector,headquarters_country,ticker,risk_score,severity,strategic_importance").order("strategic_importance", desc=True).execute()
        return {"status": "success", "category": category, "count": len(r.data or []), "items": r.data or []}

    if category in ["shipping-corridors", "shipping_corridors", "corridors"]:
        r = supabase.table("sc_shipping_corridors").select("corridor_name,origin_region,destination_region,risk_score,severity,primary_commodities,transit_chokepoints").order("risk_score", desc=True).execute()
        return {"status": "success", "category": "shipping-corridors", "count": len(r.data or []), "items": r.data or []}

    raise HTTPException(status_code=404, detail="Unsupported toolbox category")


@router.get("/risk-history/{entity_type}/{entity_name}")
async def get_supply_chain_risk_history(
    entity_type: str,
    entity_name: str,
    limit: int = 30,
):
    result = (
        supabase
        .table("sc_risk_history")
        .select("*")
        .eq("entity_type", entity_type)
        .ilike("entity_name", entity_name)
        .order("calculated_at", desc=True)
        .limit(min(max(limit, 1), 100))
        .execute()
    )

    return {
        "status": "success",
        "entity_type": entity_type,
        "entity_name": entity_name,
        "count": len(result.data or []),
        "data": result.data or [],
    }



@router.post("/recalculate-maritime-node-scores")
async def recalculate_maritime_node_scores():
    nodes_response = (
        supabase
        .table("sc_maritime_nodes")
        .select("*")
        .eq("is_active", True)
        .execute()
    )

    dependencies_response = (
        supabase
        .table("sc_port_dependencies")
        .select(
            "port_name,dependency_type,dependency_name,"
            "dependency_weight,category,notes"
        )
        .execute()
    )

    events_response = (
        supabase
        .table("sc_live_disruption_events")
        .select(
            "matched_chokepoint,severity_score,"
            "confidence_score,source,published_at"
        )
        .not_.is_("matched_chokepoint", "null")
        .execute()
    )

    assessments = calculate_all_maritime_nodes(
        nodes=nodes_response.data or [],
        dependency_rows=dependencies_response.data or [],
        live_events=events_response.data or [],
    )

    updated = []

    for assessment in assessments:
        (
            supabase
            .table("sc_maritime_nodes")
            .update({
                "baseline_risk_score": assessment["baseline_risk_score"],
                "risk_score": assessment["current_risk_score"],
                "severity": assessment["severity"],
                "strategic_importance": assessment["strategic_importance"],
                "network_dependency_score": assessment[
                    "network_dependency_score"
                ],
                "structural_vulnerability_score": assessment[
                    "structural_vulnerability_score"
                ],
                "live_signal_score": assessment["live_signal_score"],
                "confidence_score": assessment["confidence_score"],
                "score_direction": assessment["direction"],
                "model_version": assessment["model_version"],
                "last_calculated_at": assessment["last_calculated_at"],
            })
            .ilike("name", assessment["name"])
            .execute()
        )

        supabase.table("sc_risk_history").insert(
            assessment["snapshot"]
        ).execute()

        updated.append({
            key: value
            for key, value in assessment.items()
            if key != "snapshot"
        })

    return {
        "status": "success",
        "model_version": "sc-maritime-risk-v1",
        "nodes_assessed": len(assessments),
        "updated_count": len(updated),
        "updated": updated,
    }
