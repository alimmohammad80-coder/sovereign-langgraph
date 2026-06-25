def build_port_context(supabase, port_name: str):
    port_profile = (
        supabase.table("sc_master_ports")
        .select("*")
        .ilike("port_name", port_name)
        .limit(1)
        .execute()
    )

    dependencies = (
        supabase.table("sc_port_dependencies")
        .select("*")
        .ilike("port_name", port_name)
        .order("dependency_weight", desc=True)
        .execute()
    )

    companies = (
        supabase.table("sc_company_ports")
        .select("*")
        .ilike("port_name", port_name)
        .execute()
    )

    chokepoints = (
        supabase.table("sc_port_chokepoints")
        .select("*")
        .ilike("port_name", port_name)
        .execute()
    )

    corridors = (
        supabase.table("sc_shipping_corridors")
        .select("*")
        .or_(f"primary_origin_ports.cs.{{{port_name}}},primary_destination_ports.cs.{{{port_name}}}")
        .order("risk_score", desc=True)
        .execute()
    )

    live_signals = (
        supabase.table("sc_live_disruption_events")
        .select("source,title,summary,url,event_type,matched_port,matched_chokepoint,matched_commodity,matched_company,severity_score,confidence_score,published_at,ingested_at")
        .ilike("matched_port", port_name)
        .order("ingested_at", desc=True)
        .limit(10)
        .execute()
    )

    return {
        "entity_type": "port",
        "entity_name": port_name,
        "port_profile": port_profile.data[0] if port_profile.data else None,
        "dependencies": dependencies.data or [],
        "linked_companies": companies.data or [],
        "linked_chokepoints": chokepoints.data or [],
        "shipping_corridors": corridors.data or [],
        "live_signals": live_signals.data or [],
        "context_quality": {
            "has_port_profile": bool(port_profile.data),
            "dependencies_count": len(dependencies.data or []),
            "companies_count": len(companies.data or []),
            "corridors_count": len(corridors.data or []),
            "live_signals_count": len(live_signals.data or [])
        }
    }


def build_company_context(supabase, company_name: str):
    company = (
        supabase.table("sc_companies")
        .select("*")
        .ilike("company_name", company_name)
        .limit(1)
        .execute()
    )

    ports = (
        supabase.table("sc_company_ports")
        .select("*")
        .ilike("company_name", company_name)
        .execute()
    )

    suppliers = (
        supabase.table("sc_company_suppliers")
        .select("*")
        .ilike("company_name", company_name)
        .execute()
    )

    markets = (
        supabase.table("sc_company_markets")
        .select("*")
        .ilike("company_name", company_name)
        .execute()
    )

    commodities = (
        supabase.table("sc_commodity_company_exposure")
        .select("*")
        .ilike("company_name", company_name)
        .execute()
    )

    return {
        "entity_type": "company",
        "entity_name": company_name,
        "company_profile": company.data[0] if company.data else None,
        "ports": ports.data or [],
        "suppliers": suppliers.data or [],
        "markets": markets.data or [],
        "commodities": commodities.data or [],
        "context_quality": {
            "has_company_profile": bool(company.data),
            "ports_count": len(ports.data or []),
            "suppliers_count": len(suppliers.data or []),
            "commodities_count": len(commodities.data or [])
        }
    }


def build_chokepoint_context(supabase, chokepoint_name: str):
    chokepoint = (
        supabase.table("sc_chokepoints")
        .select("*")
        .ilike("name", chokepoint_name)
        .limit(1)
        .execute()
    )

    dependent_ports = (
        supabase.table("sc_port_dependencies")
        .select("*")
        .eq("dependency_type", "chokepoint")
        .ilike("dependency_name", chokepoint_name)
        .order("dependency_weight", desc=True)
        .execute()
    )

    live_signals = (
        supabase.table("sc_live_disruption_events")
        .select("source,title,summary,url,event_type,matched_chokepoint,matched_port,matched_commodity,matched_company,severity_score,confidence_score,published_at,ingested_at")
        .ilike("matched_chokepoint", chokepoint_name)
        .order("ingested_at", desc=True)
        .limit(10)
        .execute()
    )

    return {
        "entity_type": "chokepoint",
        "entity_name": chokepoint_name,
        "chokepoint_profile": chokepoint.data[0] if chokepoint.data else None,
        "dependent_ports": dependent_ports.data or [],
        "live_signals": live_signals.data or [],
        "context_quality": {
            "has_chokepoint_profile": bool(chokepoint.data),
            "dependent_ports_count": len(dependent_ports.data or []),
            "live_signals_count": len(live_signals.data or [])
        }
    }


def build_supply_chain_context(supabase, entity_type: str, entity_name: str):
    if entity_type == "port":
        return build_port_context(supabase, entity_name)

    if entity_type == "company":
        return build_company_context(supabase, entity_name)

    if entity_type == "chokepoint":
        return build_chokepoint_context(supabase, entity_name)

    return {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "context_quality": {
            "supported": False,
            "message": "Context builder for this entity type is not implemented yet."
        }
    }
