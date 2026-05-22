# routers/strategic_knowledge_graph.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
from supabase import create_client, Client

router = APIRouter(
    prefix="/api/knowledge-graph",
    tags=["Global Strategic Knowledge Graph"]
)

# ------------------------------------------------------------
# Supabase Client
# ------------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or os.getenv("SUPABASE_KEY")
)

supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def require_supabase() -> Client:
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Supabase is not configured. Missing SUPABASE_URL or SUPABASE key."
        )
    return supabase


# ------------------------------------------------------------
# Request Models
# ------------------------------------------------------------

class GraphQueryRequest(BaseModel):
    query: str = Field(..., description="Search term such as China, Taiwan Strait, oil, semiconductors")
    entity_type: Optional[str] = None
    limit: int = 20


class ImpactAnalysisRequest(BaseModel):
    entity_name: str
    depth: int = 2
    modules: Optional[List[str]] = None
    include_events: bool = True


class AddEventRequest(BaseModel):
    title: str
    summary: Optional[str] = None
    event_type: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    risk_score: int = 50
    confidence_score: int = 70
    linked_entities: Optional[List[str]] = None
    raw_payload: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

def normalize_name(value: str) -> str:
    return value.strip()


def fetch_entity_by_name(name: str):
    db = require_supabase()

    result = (
        db.table("strategic_entities")
        .select("*")
        .ilike("name", name)
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    # fallback partial search
    result = (
        db.table("strategic_entities")
        .select("*")
        .ilike("name", f"%{name}%")
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def fetch_relationships_for_entity(entity_id: str):
    db = require_supabase()

    outgoing = (
        db.table("strategic_relationships")
        .select(
            """
            *,
            source:source_entity_id(*),
            target:target_entity_id(*)
            """
        )
        .eq("source_entity_id", entity_id)
        .execute()
    )

    incoming = (
        db.table("strategic_relationships")
        .select(
            """
            *,
            source:source_entity_id(*),
            target:target_entity_id(*)
            """
        )
        .eq("target_entity_id", entity_id)
        .execute()
    )

    return {
        "outgoing": outgoing.data or [],
        "incoming": incoming.data or [],
    }


def get_connected_entities(relationships: Dict[str, List[Dict[str, Any]]]):
    connected = []

    for rel in relationships.get("outgoing", []):
        target = rel.get("target")
        if target:
            connected.append({
                "direction": "outgoing",
                "relationship_type": rel.get("relationship_type"),
                "risk_weight": rel.get("risk_weight"),
                "confidence_score": rel.get("confidence_score"),
                "entity": target,
            })

    for rel in relationships.get("incoming", []):
        source = rel.get("source")
        if source:
            connected.append({
                "direction": "incoming",
                "relationship_type": rel.get("relationship_type"),
                "risk_weight": rel.get("risk_weight"),
                "confidence_score": rel.get("confidence_score"),
                "entity": source,
            })

    connected = sorted(
        connected,
        key=lambda x: x.get("risk_weight") or 0,
        reverse=True
    )

    return connected


def build_risk_pathways(entity: Dict[str, Any], connected: List[Dict[str, Any]]):
    pathways = []

    for item in connected[:8]:
        related = item.get("entity", {})
        relationship = item.get("relationship_type", "LINKED_TO")
        risk_weight = item.get("risk_weight", 50)

        pathways.append({
            "pathway": f"{entity.get('name')} → {relationship} → {related.get('name')}",
            "source_entity": entity.get("name"),
            "relationship": relationship,
            "target_entity": related.get("name"),
            "target_type": related.get("entity_type"),
            "risk_score": risk_weight,
            "confidence_score": item.get("confidence_score", 70),
        })

    return pathways


def recommend_modules(entity: Dict[str, Any], connected: List[Dict[str, Any]]):
    name = entity.get("name", "").lower()
    entity_type = entity.get("entity_type", "").lower()
    tags = [t.lower() for t in entity.get("tags", []) or []]

    modules = set()

    if entity_type in ["country", "risk", "indicator"]:
        modules.add("Strategic Early Warning")
        modules.add("Country Intelligence")

    if entity_type in ["chokepoint", "commodity", "sector"]:
        modules.add("Supply Chain Command")

    if entity_type in ["country", "indicator", "risk"]:
        modules.add("Conflict Forecasting")

    if entity_type in ["sector", "commodity", "risk"]:
        modules.add("Financial Risk")

    if any(x in tags for x in ["shipping", "trade", "logistics", "supply_chain", "semiconductors", "energy"]):
        modules.add("Supply Chain Command")

    if any(x in tags for x in ["war", "military", "terrorism", "nuclear", "security"]):
        modules.add("Conflict Forecasting")
        modules.add("Strategic Early Warning")

    if any(x in tags for x in ["finance", "sanctions", "oil", "lng", "inflation", "markets"]):
        modules.add("Financial Risk")

    if name in ["taiwan strait", "strait of hormuz", "red sea", "south china sea"]:
        modules.add("Scenario Simulation Lab")

    modules.add("Scenario Simulation Lab")

    return list(modules)




def extract_graph_entities_from_text(
    text_value: str,
    max_entities: int = 10,
    include_related: bool = True
):
    """
    Extracts known Strategic Knowledge Graph entities from free text.

    This is deterministic and database-grounded:
    - No LLM required
    - Uses strategic_entities table
    - Matches exact entity names and tag signals
    - Optionally adds high-risk connected entities

    Example:
    "PLA Military Pressure and Taiwan Strait escalation affecting semiconductors"
    -> Taiwan, PLA Military Pressure, Taiwan Strait, Semiconductors, China, Advanced Chips
    """
    db = require_supabase()

    if not text_value:
        return {
            "matched_entities": [],
            "expanded_entities": [],
            "entity_names": [],
        }

    text_blob = text_value.lower()

    entities_result = (
        db.table("strategic_entities")
        .select("*")
        .limit(1000)
        .execute()
    )

    all_entities = entities_result.data or []

    matched = []

    for entity in all_entities:
        name = entity.get("name", "")
        entity_type = entity.get("entity_type", "")
        tags = entity.get("tags", []) or []

        if not name:
            continue

        name_lower = name.lower()
        score = 0
        reasons = []

        # Exact name match
        if name_lower in text_blob:
            score += 10
            reasons.append("matched entity name")

        # Singular/plural soft handling for common cases
        if name_lower.endswith("s"):
            singular = name_lower[:-1]
            if singular and singular in text_blob:
                score += 7
                reasons.append("matched singular form")

        # Tag match
        for tag in tags:
            tag_clean = str(tag).replace("_", " ").lower()
            if tag_clean and tag_clean in text_blob:
                score += 2
                reasons.append(f"matched tag: {tag_clean}")

        # Domain synonyms
        synonym_map = {
            "semiconductors": ["semiconductor", "chip", "chips", "tsmc", "silicon"],
            "advanced chips": ["advanced chip", "ai chip", "ai chips", "high-end chip", "high-end chips"],
            "taiwan strait": ["cross-strait", "taiwan blockade", "taiwan quarantine"],
            "pla military pressure": ["pla", "chinese military pressure", "chinese drills", "military pressure"],
            "strati of hormuz": ["hormuz"],
            "strait of hormuz": ["hormuz"],
            "red sea": ["houthi shipping", "red sea shipping"],
            "artificial intelligence": ["ai", "frontier ai", "ai compute"],
            "cyberattack": ["cyber attack", "cyber operation", "cyber operations"],
            "export controls": ["export control", "technology controls", "chip controls"],
        }

        for canonical, synonyms in synonym_map.items():
            if name_lower == canonical:
                for syn in synonyms:
                    if syn in text_blob:
                        score += 6
                        reasons.append(f"matched synonym: {syn}")

        # Avoid noisy tag-only matches such as Russia matching only because of "military".
        strong_reason = any(
            reason.startswith("matched entity name")
            or reason.startswith("matched singular form")
            or reason.startswith("matched synonym")
            for reason in reasons
        )

        if score > 0 and (strong_reason or score >= 6):
            matched.append({
                "entity": entity,
                "match_score": score,
                "match_reasons": list(dict.fromkeys(reasons)),
            })

    matched = sorted(
        matched,
        key=lambda x: (
            x.get("match_score", 0),
            x.get("entity", {}).get("importance_score", 0)
        ),
        reverse=True
    )

    matched = matched[:max_entities]

    expanded = list(matched)

    if include_related:
        seen_ids = {m["entity"]["id"] for m in matched if m.get("entity", {}).get("id")}

        for item in matched[:5]:
            entity = item.get("entity", {})
            entity_id = entity.get("id")
            if not entity_id:
                continue

            try:
                relationships = fetch_relationships_for_entity(entity_id)
                connected = get_connected_entities(relationships)

                for rel in connected[:5]:
                    related_entity = rel.get("entity")
                    if not related_entity:
                        continue

                    related_id = related_entity.get("id")
                    if not related_id or related_id in seen_ids:
                        continue

                    risk_weight = rel.get("risk_weight") or 50

                    # Only expand highly relevant/high-risk links
                    if risk_weight >= 85:
                        expanded.append({
                            "entity": related_entity,
                            "match_score": risk_weight,
                            "match_reasons": [
                                f"expanded from {entity.get('name')} via {rel.get('relationship_type')}"
                            ],
                        })
                        seen_ids.add(related_id)

            except Exception:
                continue

    expanded = sorted(
        expanded,
        key=lambda x: (
            x.get("match_score", 0),
            x.get("entity", {}).get("importance_score", 0)
        ),
        reverse=True
    )[:max_entities]

    entity_names = []
    for item in expanded:
        name = item.get("entity", {}).get("name")
        if name and name not in entity_names:
            entity_names.append(name)

    return {
        "matched_entities": matched,
        "expanded_entities": expanded,
        "entity_names": entity_names,
    }


# ------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "module": "Global Strategic Knowledge Graph",
        "supabase_configured": bool(supabase),
    }


@router.get("/overview")
def graph_overview():
    db = require_supabase()

    entities = db.table("strategic_entities").select("*").limit(500).execute()
    relationships = db.table("strategic_relationships").select("*").limit(500).execute()
    events = db.table("strategic_events").select("*").limit(25).order("created_at", desc=True).execute()

    entity_rows = entities.data or []
    relationship_rows = relationships.data or []

    counts_by_type = {}
    for entity in entity_rows:
        etype = entity.get("entity_type", "unknown")
        counts_by_type[etype] = counts_by_type.get(etype, 0) + 1

    featured_nodes = [
        e for e in entity_rows
        if e.get("importance_score", 0) >= 90
    ][:20]

    return {
        "status": "success",
        "module": "Global Strategic Knowledge Graph",
        "summary": {
            "entity_count": len(entity_rows),
            "relationship_count": len(relationship_rows),
            "recent_event_count": len(events.data or []),
            "counts_by_type": counts_by_type,
        },
        "featured_nodes": featured_nodes,
        "recent_events": events.data or [],
    }


@router.get("/entities")
def list_entities(
    entity_type: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 100
):
    db = require_supabase()

    query = db.table("strategic_entities").select("*")

    if entity_type:
        query = query.eq("entity_type", entity_type)

    if country:
        query = query.ilike("country", country)

    result = (
        query
        .order("importance_score", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "status": "success",
        "count": len(result.data or []),
        "entities": result.data or [],
    }


@router.get("/entity/{entity_name}")
def get_entity(entity_name: str):
    entity_name = normalize_name(entity_name)

    entity = fetch_entity_by_name(entity_name)

    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {entity_name}"
        )

    relationships = fetch_relationships_for_entity(entity["id"])
    connected = get_connected_entities(relationships)
    pathways = build_risk_pathways(entity, connected)
    modules = recommend_modules(entity, connected)

    return {
        "status": "success",
        "entity": entity,
        "connected_entities": connected,
        "risk_pathways": pathways,
        "recommended_modules": modules,
    }


@router.get("/relationships/{entity_name}")
def get_entity_relationships(entity_name: str):
    entity_name = normalize_name(entity_name)

    entity = fetch_entity_by_name(entity_name)

    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {entity_name}"
        )

    relationships = fetch_relationships_for_entity(entity["id"])
    connected = get_connected_entities(relationships)

    return {
        "status": "success",
        "entity": entity,
        "relationships": relationships,
        "connected_entities": connected,
    }


@router.post("/query")
def query_graph(request: GraphQueryRequest):
    db = require_supabase()

    q = f"%{request.query.strip()}%"

    query = db.table("strategic_entities").select("*").ilike("name", q)

    if request.entity_type:
        query = query.eq("entity_type", request.entity_type)

    result = (
        query
        .order("importance_score", desc=True)
        .limit(request.limit)
        .execute()
    )

    return {
        "status": "success",
        "query": request.query,
        "count": len(result.data or []),
        "results": result.data or [],
    }


@router.post("/run-impact-analysis")
def run_impact_analysis(request: ImpactAnalysisRequest):
    entity = fetch_entity_by_name(request.entity_name)

    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {request.entity_name}"
        )

    relationships = fetch_relationships_for_entity(entity["id"])
    connected = get_connected_entities(relationships)
    pathways = build_risk_pathways(entity, connected)
    modules = recommend_modules(entity, connected)

    max_connected_risk = max(
        [p.get("risk_score", 50) for p in pathways],
        default=entity.get("importance_score", 50)
    )

    overall_risk_score = round(
        (entity.get("importance_score", 50) * 0.45) +
        (max_connected_risk * 0.55)
    )

    risk_level = (
        "Critical" if overall_risk_score >= 85 else
        "High" if overall_risk_score >= 70 else
        "Guarded" if overall_risk_score >= 50 else
        "Low"
    )

    executive_judgment = (
        f"{entity.get('name')} is a {risk_level.lower()} strategic node "
        f"with direct relevance to {', '.join(modules[:3])}. "
        f"The most important exposure pathways involve "
        f"{', '.join([p['target_entity'] for p in pathways[:4] if p.get('target_entity')])}."
    )

    return {
        "status": "success",
        "entity": entity,
        "risk_score": overall_risk_score,
        "risk_level": risk_level,
        "executive_judgment": executive_judgment,
        "impact_pathways": pathways,
        "connected_entities": connected,
        "recommended_modules": modules,
        "suggested_scenarios": [
            f"What happens if {entity.get('name')} experiences a sudden disruption?",
            f"What are the second-order effects of escalation around {entity.get('name')}?",
            f"Which countries, sectors, and commodities are most exposed to {entity.get('name')}?",
            f"What early warning indicators should be monitored for {entity.get('name')}?"
        ],
    }


@router.post("/add-event")
def add_event(request: AddEventRequest):
    db = require_supabase()

    event_payload = {
        "title": request.title,
        "summary": request.summary,
        "event_type": request.event_type,
        "country": request.country,
        "region": request.region,
        "source_name": request.source_name,
        "source_url": request.source_url,
        "risk_score": request.risk_score,
        "confidence_score": request.confidence_score,
        "raw_payload": request.raw_payload or {},
    }

    event_result = (
        db.table("strategic_events")
        .insert(event_payload)
        .execute()
    )

    if not event_result.data:
        raise HTTPException(status_code=500, detail="Failed to create strategic event")

    event = event_result.data[0]
    linked = []

    if request.linked_entities:
        for entity_name in request.linked_entities:
            entity = fetch_entity_by_name(entity_name)
            if entity:
                link_result = (
                    db.table("event_entity_links")
                    .insert({
                        "event_id": event["id"],
                        "entity_id": entity["id"],
                        "relevance_score": 75,
                    })
                    .execute()
                )
                if link_result.data:
                    linked.append(entity)

    return {
        "status": "success",
        "event": event,
        "linked_entities": linked,
    }


@router.post("/run-scenario-links")
def run_scenario_links(request: ImpactAnalysisRequest):
    entity = fetch_entity_by_name(request.entity_name)

    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {request.entity_name}"
        )

    relationships = fetch_relationships_for_entity(entity["id"])
    connected = get_connected_entities(relationships)
    pathways = build_risk_pathways(entity, connected)

    scenario_prompts = []

    for pathway in pathways[:6]:
        scenario_prompts.append({
            "title": f"{entity.get('name')} disruption affecting {pathway.get('target_entity')}",
            "prompt": (
                f"Run a strategic scenario simulation assessing how disruption, escalation, "
                f"or instability involving {entity.get('name')} could affect "
                f"{pathway.get('target_entity')} through the pathway: "
                f"{pathway.get('pathway')}."
            ),
            "risk_score": pathway.get("risk_score", 50),
            "recommended_module": "Scenario Simulation Lab",
        })

    return {
        "status": "success",
        "entity": entity,
        "scenario_prompts": scenario_prompts,
    }


@router.post("/extract-entities")
def extract_entities_endpoint(request: GraphQueryRequest):
    extraction = extract_graph_entities_from_text(
        text_value=request.query,
        max_entities=request.limit or 10,
        include_related=True,
    )

    return {
        "status": "success",
        "query": request.query,
        "extraction": extraction,
    }
