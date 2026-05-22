-- ============================================================
-- Sovereign Intelligence
-- Global Strategic Knowledge Graph
-- Step 1: Core Tables
-- ============================================================

create extension if not exists "pgcrypto";

-- ------------------------------------------------------------
-- 1. Strategic Entities
-- Countries, sectors, chokepoints, companies, commodities,
-- conflicts, risks, indicators, organizations, etc.
-- ------------------------------------------------------------

create table if not exists strategic_entities (
    id uuid primary key default gen_random_uuid(),

    name text not null,
    entity_type text not null,

    country text,
    region text,

    description text,
    importance_score integer default 50 check (importance_score >= 0 and importance_score <= 100),

    tags text[] default '{}',

    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now(),

    unique(name, entity_type)
);

-- ------------------------------------------------------------
-- 2. Strategic Relationships
-- Links between entities.
-- Example:
-- China THREATENS Taiwan
-- Taiwan Strait AFFECTS Semiconductors
-- Iran THREATENS Strait of Hormuz
-- ------------------------------------------------------------

create table if not exists strategic_relationships (
    id uuid primary key default gen_random_uuid(),

    source_entity_id uuid not null references strategic_entities(id) on delete cascade,
    target_entity_id uuid not null references strategic_entities(id) on delete cascade,

    relationship_type text not null,

    confidence_score integer default 70 check (confidence_score >= 0 and confidence_score <= 100),
    risk_weight integer default 50 check (risk_weight >= 0 and risk_weight <= 100),

    evidence text,
    source_name text,
    source_url text,

    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now(),

    unique(source_entity_id, target_entity_id, relationship_type)
);

-- ------------------------------------------------------------
-- 3. Strategic Events
-- Live or historical events from GDELT, NewsAPI, ACLED, OFAC,
-- EIA, sanctions feeds, cyber feeds, etc.
-- ------------------------------------------------------------

create table if not exists strategic_events (
    id uuid primary key default gen_random_uuid(),

    title text not null,
    summary text,

    event_type text,
    country text,
    region text,

    source_name text,
    source_url text,

    event_date timestamp with time zone,
    risk_score integer default 50 check (risk_score >= 0 and risk_score <= 100),
    confidence_score integer default 70 check (confidence_score >= 0 and confidence_score <= 100),

    raw_payload jsonb default '{}'::jsonb,

    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- ------------------------------------------------------------
-- 4. Event-Entity Links
-- Connects events to graph entities.
-- Example:
-- News article about PLA drills links to China, Taiwan,
-- Taiwan Strait, PLA Military Pressure, Semiconductors.
-- ------------------------------------------------------------

create table if not exists event_entity_links (
    id uuid primary key default gen_random_uuid(),

    event_id uuid not null references strategic_events(id) on delete cascade,
    entity_id uuid not null references strategic_entities(id) on delete cascade,

    relevance_score integer default 50 check (relevance_score >= 0 and relevance_score <= 100),

    created_at timestamp with time zone default now(),

    unique(event_id, entity_id)
);

-- ------------------------------------------------------------
-- 5. User Watchlist Entities
-- Links users to graph entities they care about.
-- ------------------------------------------------------------

create table if not exists user_watchlist_entities (
    id uuid primary key default gen_random_uuid(),

    user_id uuid,
    entity_id uuid not null references strategic_entities(id) on delete cascade,

    alert_threshold integer default 70 check (alert_threshold >= 0 and alert_threshold <= 100),
    is_active boolean default true,

    created_at timestamp with time zone default now(),

    unique(user_id, entity_id)
);

-- ------------------------------------------------------------
-- 6. Graph Reports
-- Stores graph-driven reports and cross-module intelligence.
-- ------------------------------------------------------------

create table if not exists strategic_graph_reports (
    id uuid primary key default gen_random_uuid(),

    title text not null,
    entity_name text,
    report_type text,

    risk_score integer default 50 check (risk_score >= 0 and risk_score <= 100),
    confidence_score integer default 70 check (confidence_score >= 0 and confidence_score <= 100),

    executive_judgment text,
    analysis jsonb default '{}'::jsonb,

    related_modules text[] default '{}',

    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------

create index if not exists idx_strategic_entities_name
on strategic_entities using gin (to_tsvector('english', name));

create index if not exists idx_strategic_entities_type
on strategic_entities(entity_type);

create index if not exists idx_strategic_entities_country
on strategic_entities(country);

create index if not exists idx_strategic_relationships_source
on strategic_relationships(source_entity_id);

create index if not exists idx_strategic_relationships_target
on strategic_relationships(target_entity_id);

create index if not exists idx_strategic_relationships_type
on strategic_relationships(relationship_type);

create index if not exists idx_strategic_events_country
on strategic_events(country);

create index if not exists idx_strategic_events_type
on strategic_events(event_type);

create index if not exists idx_strategic_events_date
on strategic_events(event_date);

create index if not exists idx_event_entity_links_event
on event_entity_links(event_id);

create index if not exists idx_event_entity_links_entity
on event_entity_links(entity_id);

-- ------------------------------------------------------------
-- Updated-at trigger helper
-- ------------------------------------------------------------

create or replace function update_updated_at_column()
returns trigger as $$
begin
   new.updated_at = now();
   return new;
end;
$$ language plpgsql;

drop trigger if exists update_strategic_entities_updated_at on strategic_entities;
create trigger update_strategic_entities_updated_at
before update on strategic_entities
for each row
execute function update_updated_at_column();

drop trigger if exists update_strategic_relationships_updated_at on strategic_relationships;
create trigger update_strategic_relationships_updated_at
before update on strategic_relationships
for each row
execute function update_updated_at_column();

drop trigger if exists update_strategic_events_updated_at on strategic_events;
create trigger update_strategic_events_updated_at
before update on strategic_events
for each row
execute function update_updated_at_column();

drop trigger if exists update_strategic_graph_reports_updated_at on strategic_graph_reports;
create trigger update_strategic_graph_reports_updated_at
before update on strategic_graph_reports
for each row
execute function update_updated_at_column();
