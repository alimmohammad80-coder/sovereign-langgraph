import os

from dotenv import load_dotenv
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
