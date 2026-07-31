-- Sovereign Intelligence AI
-- Intelligence Knowledge Graph Core Schema
-- Migration: 20260730_003_intelligence_knowledge_graph_v2.sql
-- Purpose: Shared semantic backbone for SEWS and all intelligence modules.
-- Safe posture: additive, non-destructive, PostgreSQL-compatible, and namespaced with intel_kg_*.

begin;

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- ENUMS
-- ---------------------------------------------------------------------------

do $$
begin
    if not exists (
        select 1 from pg_type where typname = 'intel_kg_entity_status'
    ) then
        create type intel_kg_entity_status as enum (
            'ACTIVE',
            'INACTIVE',
            'MERGED',
            'DEPRECATED'
        );
    end if;

    if not exists (
        select 1 from pg_type where typname = 'intel_kg_relationship_status'
    ) then
        create type intel_kg_relationship_status as enum (
            'ACTIVE',
            'INACTIVE',
            'DISPUTED',
            'SUPERSEDED',
            'RETRACTED'
        );
    end if;

    if not exists (
        select 1 from pg_type where typname = 'intel_kg_evidence_status'
    ) then
        create type intel_kg_evidence_status as enum (
            'RAW',
            'NORMALIZED',
            'VALIDATED',
            'REJECTED',
            'ARCHIVED'
        );
    end if;

    if not exists (
        select 1 from pg_type where typname = 'intel_kg_assertion_polarity'
    ) then
        create type intel_kg_assertion_polarity as enum (
            'SUPPORTS',
            'CONTRADICTS',
            'NEUTRAL'
        );
    end if;
end
$$;

-- ---------------------------------------------------------------------------
-- UPDATED-AT FUNCTION
-- ---------------------------------------------------------------------------

create or replace function intel_kg_set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- ENTITY TYPES
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_entity_types (
    id uuid primary key default gen_random_uuid(),
    type_key text not null unique,
    name text not null,
    description text,
    parent_type_id uuid references intel_kg_entity_types(id) on delete set null,
    schema_version integer not null default 1 check (schema_version > 0),
    attributes_schema jsonb not null default '{}'::jsonb,
    is_spatial boolean not null default false,
    is_temporal boolean not null default true,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_intel_kg_entity_types_parent
    on intel_kg_entity_types(parent_type_id);

create index if not exists idx_intel_kg_entity_types_active
    on intel_kg_entity_types(active);

drop trigger if exists trg_intel_kg_entity_types_updated_at
    on intel_kg_entity_types;

create trigger trg_intel_kg_entity_types_updated_at
before update on intel_kg_entity_types
for each row execute function intel_kg_set_updated_at();

-- ---------------------------------------------------------------------------
-- ENTITIES
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_entities (
    id uuid primary key default gen_random_uuid(),
    entity_key text not null unique,
    entity_type_id uuid not null
        references intel_kg_entity_types(id) on delete restrict,
    canonical_name text not null,
    display_name text,
    description text,
    status intel_kg_entity_status not null default 'ACTIVE',
    merged_into_entity_id uuid
        references intel_kg_entities(id) on delete set null,
    country_iso3 char(3),
    region_key text,
    latitude double precision
        check (latitude is null or latitude between -90 and 90),
    longitude double precision
        check (longitude is null or longitude between -180 and 180),
    geometry_geojson jsonb,
    attributes jsonb not null default '{}'::jsonb,
    source_reliability numeric(5,2)
        check (source_reliability is null or source_reliability between 0 and 100),
    confidence numeric(5,2) not null default 50
        check (confidence between 0 and 100),
    valid_from timestamptz,
    valid_to timestamptz,
    first_seen_at timestamptz,
    last_seen_at timestamptz,
    created_by text,
    updated_by text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint intel_kg_entities_validity_check
        check (valid_to is null or valid_from is null or valid_to >= valid_from),
    constraint intel_kg_entities_merge_check
        check (merged_into_entity_id is null or merged_into_entity_id <> id)
);

create index if not exists idx_intel_kg_entities_type
    on intel_kg_entities(entity_type_id);

create index if not exists idx_intel_kg_entities_name
    on intel_kg_entities using gin (to_tsvector('simple', canonical_name));

create index if not exists idx_intel_kg_entities_country
    on intel_kg_entities(country_iso3);

create index if not exists idx_intel_kg_entities_region
    on intel_kg_entities(region_key);

create index if not exists idx_intel_kg_entities_status
    on intel_kg_entities(status);

create index if not exists idx_intel_kg_entities_last_seen
    on intel_kg_entities(last_seen_at desc);

create index if not exists idx_intel_kg_entities_attributes
    on intel_kg_entities using gin (attributes);

drop trigger if exists trg_intel_kg_entities_updated_at
    on intel_kg_entities;

create trigger trg_intel_kg_entities_updated_at
before update on intel_kg_entities
for each row execute function intel_kg_set_updated_at();

-- ---------------------------------------------------------------------------
-- ENTITY ALIASES
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_entity_aliases (
    id uuid primary key default gen_random_uuid(),
    entity_id uuid not null
        references intel_kg_entities(id) on delete cascade,
    alias text not null,
    alias_normalized text generated always as (
        lower(regexp_replace(trim(alias), '\s+', ' ', 'g'))
    ) stored,
    language_code text,
    alias_type text not null default 'NAME',
    source_key text,
    confidence numeric(5,2) not null default 80
        check (confidence between 0 and 100),
    active boolean not null default true,
    created_at timestamptz not null default now(),
    unique(entity_id, alias_normalized, alias_type)
);

create index if not exists idx_intel_kg_aliases_normalized
    on intel_kg_entity_aliases(alias_normalized);

create index if not exists idx_intel_kg_aliases_entity
    on intel_kg_entity_aliases(entity_id);

-- ---------------------------------------------------------------------------
-- RELATIONSHIP TYPES
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_relationship_types (
    id uuid primary key default gen_random_uuid(),
    relationship_key text not null unique,
    name text not null,
    inverse_relationship_key text,
    description text,
    source_entity_type_keys text[] not null default '{}'::text[],
    target_entity_type_keys text[] not null default '{}'::text[],
    is_symmetric boolean not null default false,
    is_transitive boolean not null default false,
    is_directional boolean not null default true,
    attributes_schema jsonb not null default '{}'::jsonb,
    schema_version integer not null default 1 check (schema_version > 0),
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_intel_kg_relationship_types_active
    on intel_kg_relationship_types(active);

drop trigger if exists trg_intel_kg_relationship_types_updated_at
    on intel_kg_relationship_types;

create trigger trg_intel_kg_relationship_types_updated_at
before update on intel_kg_relationship_types
for each row execute function intel_kg_set_updated_at();

-- ---------------------------------------------------------------------------
-- RELATIONSHIPS
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_relationships (
    id uuid primary key default gen_random_uuid(),
    relationship_key text not null unique,
    relationship_type_id uuid not null
        references intel_kg_relationship_types(id) on delete restrict,
    source_entity_id uuid not null
        references intel_kg_entities(id) on delete cascade,
    target_entity_id uuid not null
        references intel_kg_entities(id) on delete cascade,
    status intel_kg_relationship_status not null default 'ACTIVE',
    confidence numeric(5,2) not null default 50
        check (confidence between 0 and 100),
    source_reliability numeric(5,2)
        check (source_reliability is null or source_reliability between 0 and 100),
    strength numeric(8,4)
        check (strength is null or strength between -1 and 1),
    attributes jsonb not null default '{}'::jsonb,
    valid_from timestamptz,
    valid_to timestamptz,
    first_seen_at timestamptz,
    last_seen_at timestamptz,
    evidence_count integer not null default 0 check (evidence_count >= 0),
    created_by text,
    updated_by text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint intel_kg_relationship_self_check
        check (source_entity_id <> target_entity_id),
    constraint intel_kg_relationship_validity_check
        check (valid_to is null or valid_from is null or valid_to >= valid_from)
);

create index if not exists idx_intel_kg_relationships_source
    on intel_kg_relationships(source_entity_id);

create index if not exists idx_intel_kg_relationships_target
    on intel_kg_relationships(target_entity_id);

create index if not exists idx_intel_kg_relationships_type
    on intel_kg_relationships(relationship_type_id);

create index if not exists idx_intel_kg_relationships_status
    on intel_kg_relationships(status);

create index if not exists idx_intel_kg_relationships_last_seen
    on intel_kg_relationships(last_seen_at desc);

create index if not exists idx_intel_kg_relationships_attributes
    on intel_kg_relationships using gin (attributes);

create index if not exists idx_intel_kg_relationships_pair
    on intel_kg_relationships(source_entity_id, target_entity_id);

drop trigger if exists trg_intel_kg_relationships_updated_at
    on intel_kg_relationships;

create trigger trg_intel_kg_relationships_updated_at
before update on intel_kg_relationships
for each row execute function intel_kg_set_updated_at();

-- ---------------------------------------------------------------------------
-- RELATIONSHIP HISTORY
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_relationship_history (
    id uuid primary key default gen_random_uuid(),
    relationship_id uuid not null
        references intel_kg_relationships(id) on delete cascade,
    version_number integer not null check (version_number > 0),
    change_type text not null,
    previous_state jsonb,
    current_state jsonb not null,
    change_reason text,
    changed_by text,
    changed_at timestamptz not null default now(),
    unique(relationship_id, version_number)
);

create index if not exists idx_intel_kg_relationship_history_relationship
    on intel_kg_relationship_history(relationship_id, changed_at desc);

-- ---------------------------------------------------------------------------
-- EVIDENCE
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_evidence (
    id uuid primary key default gen_random_uuid(),
    evidence_key text not null unique,
    source_key text not null,
    source_name text,
    source_type text,
    external_id text,
    canonical_url text,
    title text,
    raw_text text,
    content_hash text,
    published_at timestamptz,
    collected_at timestamptz not null default now(),
    observed_at timestamptz,
    status intel_kg_evidence_status not null default 'RAW',
    language_code text,
    country_iso3 char(3),
    region_key text,
    latitude double precision
        check (latitude is null or latitude between -90 and 90),
    longitude double precision
        check (longitude is null or longitude between -180 and 180),
    source_reliability numeric(5,2) not null default 50
        check (source_reliability between 0 and 100),
    extraction_confidence numeric(5,2)
        check (extraction_confidence is null or extraction_confidence between 0 and 100),
    validation_confidence numeric(5,2)
        check (validation_confidence is null or validation_confidence between 0 and 100),
    duplicate_of_evidence_id uuid
        references intel_kg_evidence(id) on delete set null,
    metadata jsonb not null default '{}'::jsonb,
    raw_payload jsonb,
    collector_agent text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint intel_kg_evidence_duplicate_check
        check (duplicate_of_evidence_id is null or duplicate_of_evidence_id <> id)
);

create unique index if not exists uq_intel_kg_evidence_source_external
    on intel_kg_evidence(source_key, external_id)
    where external_id is not null;

create index if not exists idx_intel_kg_evidence_content_hash
    on intel_kg_evidence(content_hash);

create index if not exists idx_intel_kg_evidence_published
    on intel_kg_evidence(published_at desc);

create index if not exists idx_intel_kg_evidence_collected
    on intel_kg_evidence(collected_at desc);

create index if not exists idx_intel_kg_evidence_status
    on intel_kg_evidence(status);

create index if not exists idx_intel_kg_evidence_country
    on intel_kg_evidence(country_iso3);

create index if not exists idx_intel_kg_evidence_metadata
    on intel_kg_evidence using gin (metadata);

drop trigger if exists trg_intel_kg_evidence_updated_at
    on intel_kg_evidence;

create trigger trg_intel_kg_evidence_updated_at
before update on intel_kg_evidence
for each row execute function intel_kg_set_updated_at();

-- ---------------------------------------------------------------------------
-- EVIDENCE ↔ ENTITY LINKS
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_evidence_entity_links (
    id uuid primary key default gen_random_uuid(),
    evidence_id uuid not null
        references intel_kg_evidence(id) on delete cascade,
    entity_id uuid not null
        references intel_kg_entities(id) on delete cascade,
    mention_text text,
    mention_role text,
    extraction_method text,
    polarity intel_kg_assertion_polarity not null default 'NEUTRAL',
    confidence numeric(5,2) not null default 50
        check (confidence between 0 and 100),
    start_offset integer,
    end_offset integer,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique(evidence_id, entity_id, mention_role, mention_text)
);

create index if not exists idx_intel_kg_evidence_entity_evidence
    on intel_kg_evidence_entity_links(evidence_id);

create index if not exists idx_intel_kg_evidence_entity_entity
    on intel_kg_evidence_entity_links(entity_id);

-- ---------------------------------------------------------------------------
-- EVIDENCE ↔ RELATIONSHIP LINKS
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_evidence_relationship_links (
    id uuid primary key default gen_random_uuid(),
    evidence_id uuid not null
        references intel_kg_evidence(id) on delete cascade,
    relationship_id uuid not null
        references intel_kg_relationships(id) on delete cascade,
    polarity intel_kg_assertion_polarity not null default 'SUPPORTS',
    confidence numeric(5,2) not null default 50
        check (confidence between 0 and 100),
    extraction_method text,
    rationale text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique(evidence_id, relationship_id, polarity)
);

create index if not exists idx_intel_kg_evidence_relationship_evidence
    on intel_kg_evidence_relationship_links(evidence_id);

create index if not exists idx_intel_kg_evidence_relationship_relationship
    on intel_kg_evidence_relationship_links(relationship_id);

-- ---------------------------------------------------------------------------
-- GRAPH METRICS
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_entity_metrics (
    entity_id uuid primary key
        references intel_kg_entities(id) on delete cascade,
    degree_in integer not null default 0 check (degree_in >= 0),
    degree_out integer not null default 0 check (degree_out >= 0),
    degree_total integer not null default 0 check (degree_total >= 0),
    centrality_score numeric(12,8),
    pagerank_score numeric(12,8),
    betweenness_score numeric(12,8),
    risk_exposure_score numeric(5,2)
        check (risk_exposure_score is null or risk_exposure_score between 0 and 100),
    evidence_count integer not null default 0 check (evidence_count >= 0),
    metric_version text not null default 'kg-metrics-v1',
    calculated_at timestamptz not null default now()
);

create table if not exists intel_kg_relationship_metrics (
    relationship_id uuid primary key
        references intel_kg_relationships(id) on delete cascade,
    support_count integer not null default 0 check (support_count >= 0),
    contradiction_count integer not null default 0 check (contradiction_count >= 0),
    corroborated_source_count integer not null default 0
        check (corroborated_source_count >= 0),
    freshness_score numeric(5,2)
        check (freshness_score is null or freshness_score between 0 and 100),
    stability_score numeric(5,2)
        check (stability_score is null or stability_score between 0 and 100),
    metric_version text not null default 'kg-metrics-v1',
    calculated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- SEWS GRAPH LINKS
-- Connect the shared graph to SEWS without embedding scoring logic in the graph.
-- ---------------------------------------------------------------------------

create table if not exists intel_kg_sews_indicator_links (
    id uuid primary key default gen_random_uuid(),
    entity_id uuid references intel_kg_entities(id) on delete cascade,
    relationship_id uuid references intel_kg_relationships(id) on delete cascade,
    indicator_key text not null,
    link_role text not null default 'RELEVANT',
    weight numeric(8,4) not null default 1.0 check (weight >= 0),
    confidence numeric(5,2) not null default 50
        check (confidence between 0 and 100),
    active boolean not null default true,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint intel_kg_sews_indicator_link_target_check
        check (
            (entity_id is not null and relationship_id is null)
            or
            (entity_id is null and relationship_id is not null)
        )
);

create unique index if not exists uq_intel_kg_sews_entity_indicator
    on intel_kg_sews_indicator_links(entity_id, indicator_key, link_role)
    where entity_id is not null;

create unique index if not exists uq_intel_kg_sews_relationship_indicator
    on intel_kg_sews_indicator_links(relationship_id, indicator_key, link_role)
    where relationship_id is not null;

create index if not exists idx_intel_kg_sews_indicator_key
    on intel_kg_sews_indicator_links(indicator_key);

drop trigger if exists trg_intel_kg_sews_indicator_links_updated_at
    on intel_kg_sews_indicator_links;

create trigger trg_intel_kg_sews_indicator_links_updated_at
before update on intel_kg_sews_indicator_links
for each row execute function intel_kg_set_updated_at();

-- ---------------------------------------------------------------------------
-- VIEWS
-- ---------------------------------------------------------------------------

create or replace view intel_kg_entity_summary as
select
    e.id,
    e.entity_key,
    et.type_key as entity_type_key,
    et.name as entity_type_name,
    e.canonical_name,
    coalesce(e.display_name, e.canonical_name) as display_name,
    e.status,
    e.country_iso3,
    e.region_key,
    e.latitude,
    e.longitude,
    e.confidence,
    e.first_seen_at,
    e.last_seen_at,
    coalesce(m.degree_in, 0) as degree_in,
    coalesce(m.degree_out, 0) as degree_out,
    coalesce(m.degree_total, 0) as degree_total,
    m.centrality_score,
    m.risk_exposure_score,
    coalesce(m.evidence_count, 0) as evidence_count,
    e.updated_at
from intel_kg_entities e
join intel_kg_entity_types et on et.id = e.entity_type_id
left join intel_kg_entity_metrics m on m.entity_id = e.id;

create or replace view intel_kg_relationship_summary as
select
    r.id,
    r.relationship_key,
    rt.relationship_key as relationship_type_key,
    rt.name as relationship_type_name,
    r.source_entity_id,
    se.entity_key as source_entity_key,
    se.canonical_name as source_entity_name,
    r.target_entity_id,
    te.entity_key as target_entity_key,
    te.canonical_name as target_entity_name,
    r.status,
    r.confidence,
    r.strength,
    r.valid_from,
    r.valid_to,
    r.first_seen_at,
    r.last_seen_at,
    r.evidence_count,
    coalesce(rm.support_count, 0) as support_count,
    coalesce(rm.contradiction_count, 0) as contradiction_count,
    coalesce(rm.corroborated_source_count, 0) as corroborated_source_count,
    rm.freshness_score,
    r.updated_at
from intel_kg_relationships r
join intel_kg_relationship_types rt on rt.id = r.relationship_type_id
join intel_kg_entities se on se.id = r.source_entity_id
join intel_kg_entities te on te.id = r.target_entity_id
left join intel_kg_relationship_metrics rm on rm.relationship_id = r.id;

create or replace view intel_kg_evidence_provenance as
select
    ev.id as evidence_id,
    ev.evidence_key,
    ev.source_key,
    ev.source_name,
    ev.title,
    ev.published_at,
    ev.collected_at,
    ev.status,
    ev.source_reliability,
    ev.extraction_confidence,
    ev.validation_confidence,
    count(distinct eel.entity_id) as linked_entity_count,
    count(distinct erl.relationship_id) as linked_relationship_count
from intel_kg_evidence ev
left join intel_kg_evidence_entity_links eel on eel.evidence_id = ev.id
left join intel_kg_evidence_relationship_links erl on erl.evidence_id = ev.id
group by ev.id;

-- ---------------------------------------------------------------------------
-- DEFAULT ENTITY TYPES
-- ---------------------------------------------------------------------------

insert into intel_kg_entity_types (
    type_key, name, description, is_spatial, is_temporal
)
values
    ('COUNTRY', 'Country', 'Sovereign state or recognized territory.', true, true),
    ('REGION', 'Region', 'Geopolitical or geographic region.', true, true),
    ('ADMIN_AREA', 'Administrative Area', 'Province, state, district, or equivalent.', true, true),
    ('CITY', 'City', 'City or populated place.', true, true),
    ('PORT', 'Port', 'Commercial or military maritime port.', true, true),
    ('AIRPORT', 'Airport', 'Civilian or military airport.', true, true),
    ('MILITARY_BASE', 'Military Base', 'Military installation or operating site.', true, true),
    ('CHOKEPOINT', 'Chokepoint', 'Strategic maritime, land, or logistics chokepoint.', true, true),
    ('ORGANIZATION', 'Organization', 'Governmental, intergovernmental, or non-state organization.', false, true),
    ('GOVERNMENT', 'Government', 'National or subnational government.', false, true),
    ('COMPANY', 'Company', 'Commercial company or corporate entity.', false, true),
    ('MILITARY_UNIT', 'Military Unit', 'Military formation, command, or unit.', false, true),
    ('POLITICAL_PARTY', 'Political Party', 'Political party or organized political movement.', false, true),
    ('NON_STATE_ACTOR', 'Non-State Actor', 'Armed, political, or other non-state actor.', false, true),
    ('COMMODITY', 'Commodity', 'Energy, agricultural, mineral, or strategic commodity.', false, true),
    ('CURRENCY', 'Currency', 'National, supranational, or digital currency.', false, true),
    ('TECHNOLOGY', 'Technology', 'Technology, platform, or strategic technical capability.', false, true),
    ('CYBER_THREAT_ACTOR', 'Cyber Threat Actor', 'Named or tracked cyber threat actor or cluster.', false, true),
    ('EVENT', 'Event', 'Time-bounded geopolitical, economic, security, or operational event.', true, true),
    ('SANCTION_PROGRAM', 'Sanction Program', 'Sanctions regime, designation program, or restriction framework.', false, true)
on conflict (type_key) do update
set
    name = excluded.name,
    description = excluded.description,
    is_spatial = excluded.is_spatial,
    is_temporal = excluded.is_temporal,
    active = true,
    updated_at = now();

-- ---------------------------------------------------------------------------
-- DEFAULT RELATIONSHIP TYPES
-- ---------------------------------------------------------------------------

insert into intel_kg_relationship_types (
    relationship_key,
    name,
    inverse_relationship_key,
    description,
    is_symmetric,
    is_transitive,
    is_directional
)
values
    ('LOCATED_IN', 'Located In', 'CONTAINS', 'Source entity is geographically located in the target entity.', false, true, true),
    ('CONTAINS', 'Contains', 'LOCATED_IN', 'Source entity geographically contains the target entity.', false, true, true),
    ('CONTROLS', 'Controls', 'CONTROLLED_BY', 'Source entity exercises control over the target entity.', false, false, true),
    ('CONTROLLED_BY', 'Controlled By', 'CONTROLS', 'Source entity is controlled by the target entity.', false, false, true),
    ('OWNS', 'Owns', 'OWNED_BY', 'Source entity owns the target entity.', false, false, true),
    ('OWNED_BY', 'Owned By', 'OWNS', 'Source entity is owned by the target entity.', false, false, true),
    ('COMMANDS', 'Commands', 'COMMANDED_BY', 'Source entity commands the target entity.', false, false, true),
    ('COMMANDED_BY', 'Commanded By', 'COMMANDS', 'Source entity is commanded by the target entity.', false, false, true),
    ('SUPPLIES', 'Supplies', 'SUPPLIED_BY', 'Source entity supplies goods, services, or resources to the target entity.', false, false, true),
    ('SUPPLIED_BY', 'Supplied By', 'SUPPLIES', 'Source entity is supplied by the target entity.', false, false, true),
    ('TRADES_WITH', 'Trades With', 'TRADES_WITH', 'Entities maintain a trade relationship.', true, false, false),
    ('ALLIED_WITH', 'Allied With', 'ALLIED_WITH', 'Entities maintain an alliance or strategic partnership.', true, false, false),
    ('OPPOSES', 'Opposes', 'OPPOSES', 'Entities are in political, military, or strategic opposition.', true, false, false),
    ('SANCTIONED_BY', 'Sanctioned By', 'SANCTIONS', 'Source entity is sanctioned by the target entity.', false, false, true),
    ('SANCTIONS', 'Sanctions', 'SANCTIONED_BY', 'Source entity sanctions the target entity.', false, false, true),
    ('INVESTS_IN', 'Invests In', 'RECEIVES_INVESTMENT_FROM', 'Source entity invests in the target entity.', false, false, true),
    ('DEPENDS_ON', 'Depends On', 'SUPPORTS_DEPENDENCY_OF', 'Source entity depends on the target entity.', false, false, true),
    ('OPERATES_AT', 'Operates At', 'HOSTS_OPERATION_OF', 'Source entity operates at the target site.', false, false, true),
    ('CONNECTED_TO', 'Connected To', 'CONNECTED_TO', 'Entities have a material strategic connection.', true, false, false),
    ('MEMBER_OF', 'Member Of', 'HAS_MEMBER', 'Source entity is a member of the target entity.', false, false, true),
    ('PARENT_OF', 'Parent Of', 'SUBSIDIARY_OF', 'Source entity is the parent of the target entity.', false, true, true),
    ('SUBSIDIARY_OF', 'Subsidiary Of', 'PARENT_OF', 'Source entity is a subsidiary of the target entity.', false, true, true),
    ('IMPORTS_FROM', 'Imports From', 'EXPORTS_TO', 'Source entity imports goods or services from the target entity.', false, false, true),
    ('EXPORTS_TO', 'Exports To', 'IMPORTS_FROM', 'Source entity exports goods or services to the target entity.', false, false, true),
    ('DEPLOYED_TO', 'Deployed To', 'HOSTS_DEPLOYMENT_OF', 'Source military or operational entity is deployed to the target location.', false, false, true),
    ('PARTICIPATES_IN', 'Participates In', 'HAS_PARTICIPANT', 'Source entity participates in the target event or organization.', false, false, true),
    ('TARGETS', 'Targets', 'TARGETED_BY', 'Source entity targets the target entity.', false, false, true),
    ('AFFECTS', 'Affects', 'AFFECTED_BY', 'Source entity materially affects the target entity.', false, false, true)
on conflict (relationship_key) do update
set
    name = excluded.name,
    inverse_relationship_key = excluded.inverse_relationship_key,
    description = excluded.description,
    is_symmetric = excluded.is_symmetric,
    is_transitive = excluded.is_transitive,
    is_directional = excluded.is_directional,
    active = true,
    updated_at = now();

-- ---------------------------------------------------------------------------
-- ROW LEVEL SECURITY
-- Service-role/backend writes; authenticated users receive read access.
-- ---------------------------------------------------------------------------

alter table intel_kg_entity_types enable row level security;
alter table intel_kg_entities enable row level security;
alter table intel_kg_entity_aliases enable row level security;
alter table intel_kg_relationship_types enable row level security;
alter table intel_kg_relationships enable row level security;
alter table intel_kg_relationship_history enable row level security;
alter table intel_kg_evidence enable row level security;
alter table intel_kg_evidence_entity_links enable row level security;
alter table intel_kg_evidence_relationship_links enable row level security;
alter table intel_kg_entity_metrics enable row level security;
alter table intel_kg_relationship_metrics enable row level security;
alter table intel_kg_sews_indicator_links enable row level security;

do $$
declare
    table_name text;
begin
    foreach table_name in array array[
        'intel_kg_entity_types',
        'intel_kg_entities',
        'intel_kg_entity_aliases',
        'intel_kg_relationship_types',
        'intel_kg_relationships',
        'intel_kg_relationship_history',
        'intel_kg_evidence',
        'intel_kg_evidence_entity_links',
        'intel_kg_evidence_relationship_links',
        'intel_kg_entity_metrics',
        'intel_kg_relationship_metrics',
        'intel_kg_sews_indicator_links'
    ]
    loop
        execute format(
            'drop policy if exists authenticated_read on %I',
            table_name
        );
        execute format(
            'create policy authenticated_read on %I for select to authenticated using (true)',
            table_name
        );
    end loop;
end
$$;

commit;
