-- ============================================================================
-- Sovereign Intelligence AI
-- Strategic Early Warning System — Global Indicator Layer
-- Migration: 20260730_002
-- ============================================================================

create extension if not exists pgcrypto;

-- --------------------------------------------------------------------------
-- ENUM TYPES
-- --------------------------------------------------------------------------

do $$
begin
    if not exists (
        select 1 from pg_type where typname = 'sews_indicator_class'
    ) then
        create type sews_indicator_class as enum (
            'PRECURSOR',
            'ACCELERANT',
            'TRIGGER',
            'CONTRA'
        );
    end if;
end
$$;

do $$
begin
    if not exists (
        select 1 from pg_type where typname = 'sews_indicator_status'
    ) then
        create type sews_indicator_status as enum (
            'ACTIVE',
            'DARK',
            'DEGRADED',
            'PAUSED',
            'RETIRED'
        );
    end if;
end
$$;

do $$
begin
    if not exists (
        select 1 from pg_type where typname = 'sews_observation_direction'
    ) then
        create type sews_observation_direction as enum (
            'SUPPORTING',
            'CONTRARY',
            'NEUTRAL',
            'UNKNOWN'
        );
    end if;
end
$$;

do $$
begin
    if not exists (
        select 1 from pg_type where typname = 'sews_collection_method'
    ) then
        create type sews_collection_method as enum (
            'API',
            'RSS',
            'DATABASE',
            'MANUAL',
            'MODEL_DERIVED',
            'DOCUMENT',
            'SATELLITE',
            'MARITIME',
            'MARKET_DATA',
            'WEB_COLLECTION'
        );
    end if;
end
$$;

-- --------------------------------------------------------------------------
-- INDICATOR DEFINITIONS
-- One canonical record per measurable indicator.
-- --------------------------------------------------------------------------

create table if not exists sews_indicator_definitions (
    indicator_key text primary key,
    name text not null,
    description text not null,

    primary_domain text not null,
    secondary_domains text[] not null default '{}',

    default_class sews_indicator_class not null,
    status sews_indicator_status not null default 'ACTIVE',

    measurement_unit text,
    measurement_type text not null default 'NUMERIC'
        check (
            measurement_type in (
                'NUMERIC',
                'BOOLEAN',
                'CATEGORICAL',
                'TEXT',
                'EVENT_COUNT',
                'INDEX',
                'PROBABILITY'
            )
        ),

    expected_direction text not null default 'INCREASE'
        check (
            expected_direction in (
                'INCREASE',
                'DECREASE',
                'PRESENCE',
                'ABSENCE',
                'DEVIATION',
                'MIXED'
            )
        ),

    geographic_scope jsonb not null default '{}'::jsonb,
    sector_scope text[] not null default '{}',

    collection_method sews_collection_method not null,
    source_keys text[] not null default '{}',
    source_requirements jsonb not null default '{}'::jsonb,

    refresh_interval_minutes integer not null default 1440
        check (refresh_interval_minutes >= 60),

    stale_after_minutes integer not null default 4320
        check (stale_after_minutes >= refresh_interval_minutes),

    default_source_reliability numeric(5,2) not null default 70
        check (default_source_reliability between 0 and 100),

    default_relevance numeric(5,2) not null default 70
        check (default_relevance between 0 and 100),

    default_weight numeric(8,4) not null default 1.0
        check (default_weight >= 0),

    normalization_config jsonb not null default '{}'::jsonb,
    threshold_config jsonb not null default '{}'::jsonb,

    owner_agent text,
    tags text[] not null default '{}',

    version integer not null default 1
        check (version >= 1),

    active boolean not null default true,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- --------------------------------------------------------------------------
-- WARNING-PROBLEM ↔ INDICATOR MAPPING
-- The same indicator may have different meaning and weight across problems.
-- --------------------------------------------------------------------------

create table if not exists sews_warning_problem_indicators (
    id uuid primary key default gen_random_uuid(),

    problem_key text not null
        references sews_warning_problems(problem_key)
        on update cascade
        on delete cascade,

    indicator_key text not null
        references sews_indicator_definitions(indicator_key)
        on update cascade
        on delete cascade,

    indicator_class sews_indicator_class not null,

    weight numeric(8,4) not null default 1.0
        check (weight >= 0),

    polarity numeric(4,3) not null default 1.0
        check (polarity between -1 and 1),

    minimum_relevance numeric(5,2) not null default 40
        check (minimum_relevance between 0 and 100),

    minimum_reliability numeric(5,2) not null default 40
        check (minimum_reliability between 0 and 100),

    activation_threshold numeric(12,4),
    critical_threshold numeric(12,4),

    lead_time_min_days integer
        check (lead_time_min_days is null or lead_time_min_days >= 0),

    lead_time_max_days integer
        check (lead_time_max_days is null or lead_time_max_days >= 0),

    rationale text,
    collection_priority integer not null default 3
        check (collection_priority between 1 and 5),

    required boolean not null default false,
    active boolean not null default true,

    mapping_version integer not null default 1
        check (mapping_version >= 1),

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (problem_key, indicator_key),

    check (
        lead_time_min_days is null
        or lead_time_max_days is null
        or lead_time_max_days >= lead_time_min_days
    )
);

-- --------------------------------------------------------------------------
-- INDICATOR OBSERVATIONS
-- Immutable time-series evidence used by the deterministic scoring engine.
-- --------------------------------------------------------------------------

create table if not exists sews_indicator_observations (
    observation_id uuid primary key default gen_random_uuid(),

    indicator_key text not null
        references sews_indicator_definitions(indicator_key)
        on update cascade
        on delete restrict,

    problem_key text
        references sews_warning_problems(problem_key)
        on update cascade
        on delete set null,

    observed_at timestamptz not null,
    collected_at timestamptz not null default now(),

    source_key text not null,
    source_name text,
    source_url text,
    source_document_id text,

    raw_value jsonb not null default '{}'::jsonb,
    normalized_value numeric(8,6)
        check (
            normalized_value is null
            or normalized_value between 0 and 1
        ),

    direction sews_observation_direction not null default 'UNKNOWN',

    source_reliability numeric(5,2) not null
        check (source_reliability between 0 and 100),

    relevance numeric(5,2) not null
        check (relevance between 0 and 100),

    confidence numeric(5,2) not null
        check (confidence between 0 and 100),

    freshness_score numeric(5,2)
        check (
            freshness_score is null
            or freshness_score between 0 and 100
        ),

    corroboration_count integer not null default 0
        check (corroboration_count >= 0),

    evidence_summary text,
    evidence_excerpt text,

    geographic_context jsonb not null default '{}'::jsonb,
    metadata jsonb not null default '{}'::jsonb,

    deduplication_key text,
    supersedes_observation_id uuid
        references sews_indicator_observations(observation_id)
        on delete set null,

    is_dark_gap boolean not null default false,
    is_anomaly boolean not null default false,
    is_verified boolean not null default false,

    ingestion_run_id text,
    collector_agent text,

    created_at timestamptz not null default now()
);

-- --------------------------------------------------------------------------
-- COLLECTION-HEALTH TABLE
-- Tracks whether a source/indicator is healthy, degraded, or dark.
-- --------------------------------------------------------------------------

create table if not exists sews_indicator_collection_health (
    indicator_key text primary key
        references sews_indicator_definitions(indicator_key)
        on update cascade
        on delete cascade,

    status sews_indicator_status not null default 'ACTIVE',

    last_attempt_at timestamptz,
    last_success_at timestamptz,
    last_observation_at timestamptz,

    consecutive_failures integer not null default 0
        check (consecutive_failures >= 0),

    observations_24h integer not null default 0
        check (observations_24h >= 0),

    observations_7d integer not null default 0
        check (observations_7d >= 0),

    health_score numeric(5,2) not null default 100
        check (health_score between 0 and 100),

    expected_refresh_minutes integer,
    current_lag_minutes integer,

    last_error text,
    metadata jsonb not null default '{}'::jsonb,

    updated_at timestamptz not null default now()
);

-- --------------------------------------------------------------------------
-- INDEXES
-- --------------------------------------------------------------------------

create index if not exists idx_sews_indicators_domain
    on sews_indicator_definitions(primary_domain);

create index if not exists idx_sews_indicators_status
    on sews_indicator_definitions(status)
    where active = true;

create index if not exists idx_sews_indicators_owner_agent
    on sews_indicator_definitions(owner_agent);

create index if not exists idx_sews_problem_indicators_problem
    on sews_warning_problem_indicators(problem_key)
    where active = true;

create index if not exists idx_sews_problem_indicators_indicator
    on sews_warning_problem_indicators(indicator_key)
    where active = true;

create index if not exists idx_sews_problem_indicators_class
    on sews_warning_problem_indicators(problem_key, indicator_class)
    where active = true;

create index if not exists idx_sews_observations_indicator_time
    on sews_indicator_observations(indicator_key, observed_at desc);

create index if not exists idx_sews_observations_problem_time
    on sews_indicator_observations(problem_key, observed_at desc)
    where problem_key is not null;

create index if not exists idx_sews_observations_source
    on sews_indicator_observations(source_key, observed_at desc);

create index if not exists idx_sews_observations_direction
    on sews_indicator_observations(direction, observed_at desc);

create unique index if not exists idx_sews_observation_deduplication
    on sews_indicator_observations(deduplication_key)
    where deduplication_key is not null;

create index if not exists idx_sews_observations_unverified
    on sews_indicator_observations(observed_at desc)
    where is_verified = false;

create index if not exists idx_sews_collection_health_status
    on sews_indicator_collection_health(status, health_score);

-- --------------------------------------------------------------------------
-- UPDATED_AT FUNCTION AND TRIGGERS
-- --------------------------------------------------------------------------

create or replace function sews_set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_sews_indicator_definitions_updated_at
    on sews_indicator_definitions;

create trigger trg_sews_indicator_definitions_updated_at
before update on sews_indicator_definitions
for each row execute function sews_set_updated_at();

drop trigger if exists trg_sews_problem_indicators_updated_at
    on sews_warning_problem_indicators;

create trigger trg_sews_problem_indicators_updated_at
before update on sews_warning_problem_indicators
for each row execute function sews_set_updated_at();

drop trigger if exists trg_sews_collection_health_updated_at
    on sews_indicator_collection_health;

create trigger trg_sews_collection_health_updated_at
before update on sews_indicator_collection_health
for each row execute function sews_set_updated_at();

-- --------------------------------------------------------------------------
-- COLLECTION-HEALTH INITIALIZATION
-- Automatically creates a health record when an indicator is added.
-- --------------------------------------------------------------------------

create or replace function sews_initialize_indicator_health()
returns trigger
language plpgsql
as $$
begin
    insert into sews_indicator_collection_health (
        indicator_key,
        status,
        expected_refresh_minutes
    )
    values (
        new.indicator_key,
        new.status,
        new.refresh_interval_minutes
    )
    on conflict (indicator_key) do nothing;

    return new;
end;
$$;

drop trigger if exists trg_sews_initialize_indicator_health
    on sews_indicator_definitions;

create trigger trg_sews_initialize_indicator_health
after insert on sews_indicator_definitions
for each row execute function sews_initialize_indicator_health();

-- --------------------------------------------------------------------------
-- ROW-LEVEL SECURITY
-- Service-role backend retains full access.
-- Authenticated users receive read access only.
-- --------------------------------------------------------------------------

alter table sews_indicator_definitions enable row level security;
alter table sews_warning_problem_indicators enable row level security;
alter table sews_indicator_observations enable row level security;
alter table sews_indicator_collection_health enable row level security;

drop policy if exists "Authenticated users read SEWS indicators"
    on sews_indicator_definitions;

create policy "Authenticated users read SEWS indicators"
on sews_indicator_definitions
for select
to authenticated
using (active = true);

drop policy if exists "Authenticated users read SEWS mappings"
    on sews_warning_problem_indicators;

create policy "Authenticated users read SEWS mappings"
on sews_warning_problem_indicators
for select
to authenticated
using (active = true);

drop policy if exists "Authenticated users read SEWS observations"
    on sews_indicator_observations;

create policy "Authenticated users read SEWS observations"
on sews_indicator_observations
for select
to authenticated
using (true);

drop policy if exists "Authenticated users read SEWS collection health"
    on sews_indicator_collection_health;

create policy "Authenticated users read SEWS collection health"
on sews_indicator_collection_health
for select
to authenticated
using (true);

-- --------------------------------------------------------------------------
-- READ VIEW FOR THE FRONTEND AND API
-- --------------------------------------------------------------------------

create or replace view sews_warning_problem_indicator_summary as
select
    wpi.problem_key,
    wp.title as warning_problem_title,
    wp.state as warning_state,

    count(*) filter (
        where wpi.active = true
    ) as indicator_count,

    count(*) filter (
        where wpi.active = true
        and wpi.indicator_class = 'PRECURSOR'
    ) as precursor_count,

    count(*) filter (
        where wpi.active = true
        and wpi.indicator_class = 'ACCELERANT'
    ) as accelerant_count,

    count(*) filter (
        where wpi.active = true
        and wpi.indicator_class = 'TRIGGER'
    ) as trigger_count,

    count(*) filter (
        where wpi.active = true
        and wpi.indicator_class = 'CONTRA'
    ) as contrary_count,

    count(*) filter (
        where wpi.active = true
        and ch.status = 'DARK'
    ) as dark_indicator_count,

    round(
        avg(ch.health_score) filter (
            where wpi.active = true
        ),
        2
    ) as average_collection_health

from sews_warning_problem_indicators wpi

join sews_warning_problems wp
    on wp.problem_key = wpi.problem_key

join sews_indicator_definitions indicator
    on indicator.indicator_key = wpi.indicator_key

left join sews_indicator_collection_health ch
    on ch.indicator_key = wpi.indicator_key

group by
    wpi.problem_key,
    wp.title,
    wp.state;

comment on table sews_indicator_definitions is
'Canonical SEWS indicator library designed to scale beyond 5,000 indicators.';

comment on table sews_warning_problem_indicators is
'Context-specific mapping of indicators to standing warning problems.';

comment on table sews_indicator_observations is
'Immutable timestamped evidence collected for deterministic warning assessments.';

comment on table sews_indicator_collection_health is
'Collection-health and dark-feed monitoring for every SEWS indicator.';
