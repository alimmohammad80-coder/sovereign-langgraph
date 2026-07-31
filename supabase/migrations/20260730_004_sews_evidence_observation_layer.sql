-- Sovereign Intelligence AI
-- SEWS Evidence and Observation Layer
-- Migration: 20260730_004_sews_evidence_observation_layer.sql
-- Purpose: Operational evidence, observation, and indicator-state backend for SEWS.
-- Design: Additive, non-destructive, deterministic-engine friendly, and linked to the Intelligence Knowledge Graph.

begin;

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- ENUMS
-- ---------------------------------------------------------------------------

do $$
begin
    if not exists (
        select 1 from pg_type where typname = 'sews_source_status'
    ) then
        create type sews_source_status as enum (
            'ACTIVE',
            'DEGRADED',
            'PAUSED',
            'INACTIVE'
        );
    end if;

    if not exists (
        select 1 from pg_type where typname = 'sews_evidence_status'
    ) then
        create type sews_evidence_status as enum (
            'RAW',
            'NORMALIZED',
            'VALIDATED',
            'REJECTED',
            'ARCHIVED'
        );
    end if;

    if not exists (
        select 1 from pg_type where typname = 'sews_evidence_polarity'
    ) then
        create type sews_evidence_polarity as enum (
            'SUPPORTING',
            'CONTRADICTING',
            'NEUTRAL'
        );
    end if;

    if not exists (
        select 1 from pg_type where typname = 'sews_observation_status'
    ) then
        create type sews_observation_status as enum (
            'DRAFT',
            'VALIDATED',
            'SUPERSEDED',
            'REJECTED'
        );
    end if;

    if not exists (
        select 1 from pg_type where typname = 'sews_observation_trend'
    ) then
        create type sews_observation_trend as enum (
            'RISING',
            'STABLE',
            'FALLING',
            'VOLATILE',
            'UNKNOWN'
        );
    end if;

    if not exists (
        select 1 from pg_type where typname = 'sews_indicator_state_status'
    ) then
        create type sews_indicator_state_status as enum (
            'ACTIVE',
            'STALE',
            'INSUFFICIENT_EVIDENCE',
            'DEGRADED',
            'INACTIVE'
        );
    end if;
end
$$;

-- ---------------------------------------------------------------------------
-- UPDATED-AT FUNCTION
-- ---------------------------------------------------------------------------

create or replace function sews_set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- DATA SOURCES
-- ---------------------------------------------------------------------------

create table if not exists sews_sources (
    id uuid primary key default gen_random_uuid(),
    source_key text not null unique,
    name text not null,
    source_type text not null,
    provider text,
    description text,
    base_url text,
    ownership_type text,
    access_tier text not null default 'OPEN',
    license_name text,
    license_url text,
    authentication_type text,
    update_cadence_minutes integer
        check (update_cadence_minutes is null or update_cadence_minutes > 0),
    default_reliability numeric(5,2) not null default 50
        check (default_reliability between 0 and 100),
    geographic_coverage text[] not null default '{}'::text[],
    domain_coverage text[] not null default '{}'::text[],
    status sews_source_status not null default 'ACTIVE',
    health_score numeric(5,2) not null default 100
        check (health_score between 0 and 100),
    last_success_at timestamptz,
    last_failure_at timestamptz,
    failure_count integer not null default 0 check (failure_count >= 0),
    configuration jsonb not null default '{}'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_sews_sources_status
    on sews_sources(status);

create index if not exists idx_sews_sources_type
    on sews_sources(source_type);

create index if not exists idx_sews_sources_domains
    on sews_sources using gin(domain_coverage);

drop trigger if exists trg_sews_sources_updated_at on sews_sources;

create trigger trg_sews_sources_updated_at
before update on sews_sources
for each row execute function sews_set_updated_at();

-- ---------------------------------------------------------------------------
-- RAW EVIDENCE
-- Immutable collection record. No analytical judgment should be stored here.
-- ---------------------------------------------------------------------------

create table if not exists sews_raw_evidence (
    id uuid primary key default gen_random_uuid(),
    evidence_key text not null unique,
    source_id uuid not null
        references sews_sources(id) on delete restrict,
    source_external_id text,
    canonical_url text,
    title text,
    raw_text text,
    raw_payload jsonb,
    content_type text,
    content_hash text,
    language_code text,
    published_at timestamptz,
    observed_at timestamptz,
    collected_at timestamptz not null default now(),
    collector_agent text,
    collection_run_id uuid,
    country_iso3 char(3),
    region_key text,
    latitude double precision
        check (latitude is null or latitude between -90 and 90),
    longitude double precision
        check (longitude is null or longitude between -180 and 180),
    status sews_evidence_status not null default 'RAW',
    duplicate_of_id uuid
        references sews_raw_evidence(id) on delete set null,
    retention_until timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    constraint sews_raw_evidence_duplicate_check
        check (duplicate_of_id is null or duplicate_of_id <> id)
);

create unique index if not exists uq_sews_raw_evidence_source_external
    on sews_raw_evidence(source_id, source_external_id)
    where source_external_id is not null;

create index if not exists idx_sews_raw_evidence_hash
    on sews_raw_evidence(content_hash);

create index if not exists idx_sews_raw_evidence_published
    on sews_raw_evidence(published_at desc);

create index if not exists idx_sews_raw_evidence_collected
    on sews_raw_evidence(collected_at desc);

create index if not exists idx_sews_raw_evidence_status
    on sews_raw_evidence(status);

create index if not exists idx_sews_raw_evidence_country
    on sews_raw_evidence(country_iso3);

create index if not exists idx_sews_raw_evidence_payload
    on sews_raw_evidence using gin(raw_payload);

-- ---------------------------------------------------------------------------
-- NORMALIZED EVIDENCE OBJECTS
-- Structured analytical representation derived from raw evidence.
-- ---------------------------------------------------------------------------

create table if not exists sews_evidence_objects (
    id uuid primary key default gen_random_uuid(),
    evidence_object_key text not null unique,
    raw_evidence_id uuid not null
        references sews_raw_evidence(id) on delete cascade,
    evidence_type text not null,
    event_type text,
    summary text,
    normalized_text text,
    event_time timestamptz,
    country_iso3 char(3),
    region_key text,
    latitude double precision
        check (latitude is null or latitude between -90 and 90),
    longitude double precision
        check (longitude is null or longitude between -180 and 180),
    entity_ids uuid[] not null default '{}'::uuid[],
    relationship_ids uuid[] not null default '{}'::uuid[],
    kg_evidence_id uuid
        references intel_kg_evidence(id) on delete set null,
    polarity sews_evidence_polarity not null default 'NEUTRAL',
    source_reliability numeric(5,2) not null
        check (source_reliability between 0 and 100),
    extraction_confidence numeric(5,2) not null
        check (extraction_confidence between 0 and 100),
    validation_confidence numeric(5,2)
        check (validation_confidence is null or validation_confidence between 0 and 100),
    corroboration_count integer not null default 0
        check (corroboration_count >= 0),
    duplicate_cluster_key text,
    contradiction_cluster_key text,
    status sews_evidence_status not null default 'NORMALIZED',
    extractor_version text,
    validator_version text,
    attributes jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_sews_evidence_objects_raw
    on sews_evidence_objects(raw_evidence_id);

create index if not exists idx_sews_evidence_objects_event_time
    on sews_evidence_objects(event_time desc);

create index if not exists idx_sews_evidence_objects_country
    on sews_evidence_objects(country_iso3);

create index if not exists idx_sews_evidence_objects_status
    on sews_evidence_objects(status);

create index if not exists idx_sews_evidence_objects_kg
    on sews_evidence_objects(kg_evidence_id);

create index if not exists idx_sews_evidence_objects_attributes
    on sews_evidence_objects using gin(attributes);

drop trigger if exists trg_sews_evidence_objects_updated_at
    on sews_evidence_objects;

create trigger trg_sews_evidence_objects_updated_at
before update on sews_evidence_objects
for each row execute function sews_set_updated_at();

-- ---------------------------------------------------------------------------
-- OBSERVATIONS
-- Derived analytical claims supported by one or more normalized evidence objects.
-- ---------------------------------------------------------------------------

create table if not exists sews_observations (
    id uuid primary key default gen_random_uuid(),
    observation_key text not null unique,
    indicator_key text not null,
    warning_problem_key text,
    analytic_framework_key text,
    indicator_group_key text,
    title text not null,
    statement text not null,
    normalized_value numeric(8,4)
        check (normalized_value is null or normalized_value between 0 and 1),
    raw_value numeric,
    unit text,
    polarity sews_evidence_polarity not null default 'NEUTRAL',
    trend sews_observation_trend not null default 'UNKNOWN',
    confidence numeric(5,2) not null
        check (confidence between 0 and 100),
    evidence_count integer not null default 0
        check (evidence_count >= 0),
    corroborated_source_count integer not null default 0
        check (corroborated_source_count >= 0),
    source_reliability_mean numeric(5,2)
        check (
            source_reliability_mean is null
            or source_reliability_mean between 0 and 100
        ),
    freshness_score numeric(5,2)
        check (freshness_score is null or freshness_score between 0 and 100),
    observed_at timestamptz not null,
    valid_from timestamptz,
    valid_to timestamptz,
    country_iso3 char(3),
    region_key text,
    latitude double precision
        check (latitude is null or latitude between -90 and 90),
    longitude double precision
        check (longitude is null or longitude between -180 and 180),
    status sews_observation_status not null default 'DRAFT',
    supersedes_observation_id uuid
        references sews_observations(id) on delete set null,
    generation_method text not null default 'RULE_BASED',
    generator_version text,
    analyst_reviewed boolean not null default false,
    reviewed_by text,
    reviewed_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint sews_observations_validity_check
        check (valid_to is null or valid_from is null or valid_to >= valid_from),
    constraint sews_observations_supersedes_check
        check (
            supersedes_observation_id is null
            or supersedes_observation_id <> id
        )
);

create index if not exists idx_sews_observations_indicator
    on sews_observations(indicator_key);

create index if not exists idx_sews_observations_warning
    on sews_observations(warning_problem_key);

create index if not exists idx_sews_observations_framework
    on sews_observations(analytic_framework_key);

create index if not exists idx_sews_observations_group
    on sews_observations(indicator_group_key);

create index if not exists idx_sews_observations_observed_at
    on sews_observations(observed_at desc);

create index if not exists idx_sews_observations_status
    on sews_observations(status);

create index if not exists idx_sews_observations_country
    on sews_observations(country_iso3);

create index if not exists idx_sews_observations_metadata
    on sews_observations using gin(metadata);

drop trigger if exists trg_sews_observations_updated_at
    on sews_observations;

create trigger trg_sews_observations_updated_at
before update on sews_observations
for each row execute function sews_set_updated_at();

-- ---------------------------------------------------------------------------
-- OBSERVATION ↔ EVIDENCE LINKS
-- ---------------------------------------------------------------------------

create table if not exists sews_observation_evidence_links (
    id uuid primary key default gen_random_uuid(),
    observation_id uuid not null
        references sews_observations(id) on delete cascade,
    evidence_object_id uuid not null
        references sews_evidence_objects(id) on delete cascade,
    polarity sews_evidence_polarity not null default 'SUPPORTING',
    contribution_weight numeric(8,4) not null default 1.0
        check (contribution_weight >= 0),
    confidence numeric(5,2) not null
        check (confidence between 0 and 100),
    rationale text,
    created_at timestamptz not null default now(),
    unique(observation_id, evidence_object_id, polarity)
);

create index if not exists idx_sews_obs_evidence_observation
    on sews_observation_evidence_links(observation_id);

create index if not exists idx_sews_obs_evidence_object
    on sews_observation_evidence_links(evidence_object_id);

-- ---------------------------------------------------------------------------
-- CURRENT INDICATOR STATE
-- One current state per indicator and analytical context.
-- ---------------------------------------------------------------------------

create table if not exists sews_indicator_state (
    id uuid primary key default gen_random_uuid(),
    state_key text not null unique,
    indicator_key text not null,
    warning_problem_key text,
    analytic_framework_key text,
    indicator_group_key text,
    country_iso3 char(3),
    region_key text,
    current_value numeric(8,4)
        check (current_value is null or current_value between 0 and 1),
    previous_value numeric(8,4)
        check (previous_value is null or previous_value between 0 and 1),
    delta numeric(8,4),
    trend sews_observation_trend not null default 'UNKNOWN',
    confidence numeric(5,2) not null default 0
        check (confidence between 0 and 100),
    evidence_count integer not null default 0
        check (evidence_count >= 0),
    supporting_evidence_count integer not null default 0
        check (supporting_evidence_count >= 0),
    contradicting_evidence_count integer not null default 0
        check (contradicting_evidence_count >= 0),
    corroborated_source_count integer not null default 0
        check (corroborated_source_count >= 0),
    freshness_score numeric(5,2) not null default 0
        check (freshness_score between 0 and 100),
    latest_observation_id uuid
        references sews_observations(id) on delete set null,
    status sews_indicator_state_status not null
        default 'INSUFFICIENT_EVIDENCE',
    stale_after timestamptz,
    last_observed_at timestamptz,
    last_calculated_at timestamptz not null default now(),
    calculation_version text not null default 'sews-indicator-state-v1',
    state_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_sews_indicator_state_context
    on sews_indicator_state(
        indicator_key,
        coalesce(warning_problem_key, ''),
        coalesce(analytic_framework_key, ''),
        coalesce(indicator_group_key, ''),
        coalesce(country_iso3, ''),
        coalesce(region_key, '')
    );

create index if not exists idx_sews_indicator_state_indicator
    on sews_indicator_state(indicator_key);

create index if not exists idx_sews_indicator_state_warning
    on sews_indicator_state(warning_problem_key);

create index if not exists idx_sews_indicator_state_status
    on sews_indicator_state(status);

create index if not exists idx_sews_indicator_state_country
    on sews_indicator_state(country_iso3);

create index if not exists idx_sews_indicator_state_stale
    on sews_indicator_state(stale_after);

drop trigger if exists trg_sews_indicator_state_updated_at
    on sews_indicator_state;

create trigger trg_sews_indicator_state_updated_at
before update on sews_indicator_state
for each row execute function sews_set_updated_at();

-- ---------------------------------------------------------------------------
-- INDICATOR STATE HISTORY
-- Immutable calculation history for reproducibility and trend analysis.
-- ---------------------------------------------------------------------------

create table if not exists sews_indicator_state_history (
    id uuid primary key default gen_random_uuid(),
    indicator_state_id uuid not null
        references sews_indicator_state(id) on delete cascade,
    indicator_key text not null,
    warning_problem_key text,
    analytic_framework_key text,
    indicator_group_key text,
    country_iso3 char(3),
    region_key text,
    value numeric(8,4)
        check (value is null or value between 0 and 1),
    trend sews_observation_trend not null default 'UNKNOWN',
    confidence numeric(5,2) not null
        check (confidence between 0 and 100),
    evidence_count integer not null default 0
        check (evidence_count >= 0),
    supporting_evidence_count integer not null default 0
        check (supporting_evidence_count >= 0),
    contradicting_evidence_count integer not null default 0
        check (contradicting_evidence_count >= 0),
    freshness_score numeric(5,2)
        check (freshness_score is null or freshness_score between 0 and 100),
    status sews_indicator_state_status not null,
    calculation_version text not null,
    calculation_input jsonb not null default '{}'::jsonb,
    calculated_at timestamptz not null default now()
);

create index if not exists idx_sews_indicator_history_state
    on sews_indicator_state_history(
        indicator_state_id,
        calculated_at desc
    );

create index if not exists idx_sews_indicator_history_indicator
    on sews_indicator_state_history(
        indicator_key,
        calculated_at desc
    );

create index if not exists idx_sews_indicator_history_warning
    on sews_indicator_state_history(
        warning_problem_key,
        calculated_at desc
    );

-- ---------------------------------------------------------------------------
-- HELPER FUNCTION: RECORD INDICATOR STATE HISTORY
-- ---------------------------------------------------------------------------

create or replace function sews_record_indicator_state_history()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'UPDATE' and (
        old.current_value is distinct from new.current_value
        or old.confidence is distinct from new.confidence
        or old.trend is distinct from new.trend
        or old.status is distinct from new.status
        or old.evidence_count is distinct from new.evidence_count
    ) then
        insert into sews_indicator_state_history (
            indicator_state_id,
            indicator_key,
            warning_problem_key,
            analytic_framework_key,
            indicator_group_key,
            country_iso3,
            region_key,
            value,
            trend,
            confidence,
            evidence_count,
            supporting_evidence_count,
            contradicting_evidence_count,
            freshness_score,
            status,
            calculation_version,
            calculation_input,
            calculated_at
        )
        values (
            new.id,
            new.indicator_key,
            new.warning_problem_key,
            new.analytic_framework_key,
            new.indicator_group_key,
            new.country_iso3,
            new.region_key,
            new.current_value,
            new.trend,
            new.confidence,
            new.evidence_count,
            new.supporting_evidence_count,
            new.contradicting_evidence_count,
            new.freshness_score,
            new.status,
            new.calculation_version,
            new.state_metadata,
            new.last_calculated_at
        );
    end if;

    return new;
end;
$$;

drop trigger if exists trg_sews_indicator_state_history
    on sews_indicator_state;

create trigger trg_sews_indicator_state_history
after update on sews_indicator_state
for each row execute function sews_record_indicator_state_history();

-- ---------------------------------------------------------------------------
-- VIEWS
-- ---------------------------------------------------------------------------

create or replace view sews_evidence_pipeline_summary as
select
    s.source_key,
    s.name as source_name,
    s.status as source_status,
    count(distinct re.id) as raw_evidence_count,
    count(distinct eo.id) as evidence_object_count,
    count(distinct oel.observation_id) as linked_observation_count,
    max(re.collected_at) as last_collected_at,
    max(eo.updated_at) as last_normalized_at
from sews_sources s
left join sews_raw_evidence re on re.source_id = s.id
left join sews_evidence_objects eo on eo.raw_evidence_id = re.id
left join sews_observation_evidence_links oel
    on oel.evidence_object_id = eo.id
group by s.id;

create or replace view sews_observation_summary as
select
    o.id,
    o.observation_key,
    o.indicator_key,
    o.warning_problem_key,
    o.analytic_framework_key,
    o.indicator_group_key,
    o.title,
    o.statement,
    o.normalized_value,
    o.polarity,
    o.trend,
    o.confidence,
    o.status,
    o.country_iso3,
    o.region_key,
    o.observed_at,
    count(distinct oel.evidence_object_id) as linked_evidence_count,
    count(distinct re.source_id) as distinct_source_count,
    avg(eo.source_reliability) as mean_source_reliability,
    o.updated_at
from sews_observations o
left join sews_observation_evidence_links oel
    on oel.observation_id = o.id
left join sews_evidence_objects eo
    on eo.id = oel.evidence_object_id
left join sews_raw_evidence re
    on re.id = eo.raw_evidence_id
group by o.id;

create or replace view sews_current_indicator_state as
select
    s.id,
    s.state_key,
    s.indicator_key,
    s.warning_problem_key,
    s.analytic_framework_key,
    s.indicator_group_key,
    s.country_iso3,
    s.region_key,
    s.current_value,
    s.previous_value,
    s.delta,
    s.trend,
    s.confidence,
    s.evidence_count,
    s.supporting_evidence_count,
    s.contradicting_evidence_count,
    s.corroborated_source_count,
    s.freshness_score,
    s.status,
    s.stale_after,
    s.last_observed_at,
    s.last_calculated_at,
    o.observation_key as latest_observation_key,
    o.title as latest_observation_title
from sews_indicator_state s
left join sews_observations o on o.id = s.latest_observation_id;

-- ---------------------------------------------------------------------------
-- DEFAULT OPEN AND PUBLIC SOURCES
-- Credentials are never stored here; only source metadata.
-- ---------------------------------------------------------------------------

insert into sews_sources (
    source_key,
    name,
    source_type,
    provider,
    description,
    base_url,
    ownership_type,
    access_tier,
    update_cadence_minutes,
    default_reliability,
    domain_coverage
)
values
    (
        'WORLD_BANK',
        'World Bank Open Data',
        'ECONOMIC_DATA',
        'World Bank',
        'Global development, economic, population, and governance indicators.',
        'https://api.worldbank.org',
        'INTERGOVERNMENTAL',
        'OPEN',
        1440,
        90,
        array['Economic and Financial', 'Political Stability', 'Humanitarian and Public Health']
    ),
    (
        'IMF',
        'International Monetary Fund Data',
        'ECONOMIC_DATA',
        'International Monetary Fund',
        'Macroeconomic, fiscal, monetary, debt, and external-sector data.',
        'https://www.imf.org',
        'INTERGOVERNMENTAL',
        'OPEN',
        1440,
        90,
        array['Economic and Financial']
    ),
    (
        'FRED',
        'Federal Reserve Economic Data',
        'ECONOMIC_DATA',
        'Federal Reserve Bank of St. Louis',
        'Macroeconomic, financial-market, commodity, and monetary indicators.',
        'https://fred.stlouisfed.org',
        'PUBLIC',
        'OPEN',
        360,
        90,
        array['Economic and Financial', 'Energy and Supply Chain']
    ),
    (
        'GDELT',
        'GDELT Project',
        'EVENT_DATA',
        'GDELT Project',
        'Global event, media, and narrative monitoring data.',
        'https://www.gdeltproject.org',
        'OPEN_RESEARCH',
        'OPEN',
        15,
        70,
        array[
            'Conflict and Military',
            'Political Stability',
            'Cyber and Information Operations',
            'Humanitarian and Public Health'
        ]
    ),
    (
        'RELIEFWEB',
        'ReliefWeb',
        'HUMANITARIAN_DATA',
        'United Nations OCHA',
        'Humanitarian reports, disasters, crises, and response information.',
        'https://reliefweb.int',
        'INTERGOVERNMENTAL',
        'OPEN',
        60,
        85,
        array['Humanitarian and Public Health', 'Climate and Environmental Risk']
    ),
    (
        'OFAC',
        'OFAC Sanctions Data',
        'SANCTIONS_DATA',
        'U.S. Department of the Treasury',
        'Sanctions programs, designated entities, and restrictions.',
        'https://ofac.treasury.gov',
        'PUBLIC',
        'OPEN',
        360,
        95,
        array[
            'Economic and Financial',
            'Political Stability',
            'Corporate and Strategic Exposure'
        ]
    ),
    (
        'EIA',
        'U.S. Energy Information Administration',
        'ENERGY_DATA',
        'U.S. Energy Information Administration',
        'Energy production, trade, inventory, price, and market data.',
        'https://www.eia.gov',
        'PUBLIC',
        'OPEN',
        360,
        90,
        array['Energy and Supply Chain', 'Economic and Financial']
    ),
    (
        'UN_COMTRADE',
        'UN Comtrade',
        'TRADE_DATA',
        'United Nations Statistics Division',
        'Global commodity trade and bilateral trade-flow data.',
        'https://comtradeplus.un.org',
        'INTERGOVERNMENTAL',
        'OPEN',
        1440,
        90,
        array['Energy and Supply Chain', 'Economic and Financial', 'Corporate and Strategic Exposure']
    )
on conflict (source_key) do update
set
    name = excluded.name,
    source_type = excluded.source_type,
    provider = excluded.provider,
    description = excluded.description,
    base_url = excluded.base_url,
    ownership_type = excluded.ownership_type,
    access_tier = excluded.access_tier,
    update_cadence_minutes = excluded.update_cadence_minutes,
    default_reliability = excluded.default_reliability,
    domain_coverage = excluded.domain_coverage,
    status = 'ACTIVE',
    updated_at = now();

-- ---------------------------------------------------------------------------
-- ROW LEVEL SECURITY
-- Authenticated users receive read access. Writes remain backend/service-role.
-- ---------------------------------------------------------------------------

alter table sews_sources enable row level security;
alter table sews_raw_evidence enable row level security;
alter table sews_evidence_objects enable row level security;
alter table sews_observations enable row level security;
alter table sews_observation_evidence_links enable row level security;
alter table sews_indicator_state enable row level security;
alter table sews_indicator_state_history enable row level security;

do $$
declare
    target_table text;
begin
    foreach target_table in array array[
        'sews_sources',
        'sews_raw_evidence',
        'sews_evidence_objects',
        'sews_observations',
        'sews_observation_evidence_links',
        'sews_indicator_state',
        'sews_indicator_state_history'
    ]
    loop
        execute format(
            'drop policy if exists authenticated_read on %I',
            target_table
        );

        execute format(
            'create policy authenticated_read on %I for select to authenticated using (true)',
            target_table
        );
    end loop;
end
$$;

commit;
