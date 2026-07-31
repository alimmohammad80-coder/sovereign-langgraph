begin;

create extension if not exists pgcrypto;

-- ============================================================
-- ENUMS
-- ============================================================

do $$
begin
    create type intelligence_observation_direction as enum (
        'INCREASING',
        'DECREASING',
        'STABLE',
        'MIXED',
        'UNKNOWN'
    );
exception
    when duplicate_object then null;
end $$;

do $$
begin
    create type intelligence_observation_status as enum (
        'ACTIVE',
        'SUPERSEDED',
        'EXPIRED',
        'REJECTED'
    );
exception
    when duplicate_object then null;
end $$;

do $$
begin
    create type intelligence_materiality_level as enum (
        'LOW',
        'MODERATE',
        'HIGH',
        'CRITICAL'
    );
exception
    when duplicate_object then null;
end $$;

-- ============================================================
-- OBSERVATIONS
-- ============================================================

create table if not exists intelligence_observations (
    id uuid primary key default gen_random_uuid(),

    observation_key text not null unique,

    title text not null,
    summary text not null,
    observation_type text not null,

    source_key text not null,
    source_record_id text,
    evidence_id uuid,
    canonical_record_id text,

    country_iso3 varchar(3),
    region_key text,

    direction intelligence_observation_direction
        not null default 'UNKNOWN',

    severity numeric(5,2)
        not null default 0
        check (severity >= 0 and severity <= 100),

    confidence numeric(6,5)
        not null default 0.5
        check (confidence >= 0 and confidence <= 1),

    source_reliability numeric(6,5)
        not null default 0.5
        check (
            source_reliability >= 0
            and source_reliability <= 1
        ),

    novelty numeric(6,5)
        not null default 0.5
        check (novelty >= 0 and novelty <= 1),

    materiality_score numeric(5,2)
        not null default 0
        check (
            materiality_score >= 0
            and materiality_score <= 100
        ),

    materiality_level intelligence_materiality_level
        not null default 'LOW',

    is_material boolean not null default false,

    status intelligence_observation_status
        not null default 'ACTIVE',

    effective_at timestamptz not null default now(),
    expires_at timestamptz,

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ============================================================
-- OBSERVATION ↔ ENTITIES
-- ============================================================

create table if not exists intelligence_observation_entities (
    id uuid primary key default gen_random_uuid(),

    observation_id uuid not null
        references intelligence_observations(id)
        on delete cascade,

    entity_type text not null,
    entity_name text not null,
    canonical_name text,
    external_id text,
    country_iso3 varchar(3),

    knowledge_graph_entity_id uuid,

    confidence numeric(6,5)
        not null default 0.5
        check (confidence >= 0 and confidence <= 1),

    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),

    unique (
        observation_id,
        entity_type,
        entity_name
    )
);

-- ============================================================
-- OBSERVATION ↔ INDICATORS
-- ============================================================

create table if not exists intelligence_observation_indicators (
    id uuid primary key default gen_random_uuid(),

    observation_id uuid not null
        references intelligence_observations(id)
        on delete cascade,

    indicator_key text not null,

    impact_score numeric(6,2)
        not null
        check (
            impact_score >= -100
            and impact_score <= 100
        ),

    confidence numeric(6,5)
        not null
        check (confidence >= 0 and confidence <= 1),

    mapping_rule text not null,
    rationale text,

    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),

    unique (
        observation_id,
        indicator_key
    )
);

-- ============================================================
-- OBSERVATION RELATIONSHIPS
-- ============================================================

create table if not exists intelligence_observation_relationships (
    id uuid primary key default gen_random_uuid(),

    source_observation_id uuid not null
        references intelligence_observations(id)
        on delete cascade,

    target_observation_id uuid not null
        references intelligence_observations(id)
        on delete cascade,

    relationship_type text not null,

    confidence numeric(6,5)
        not null default 0.5
        check (confidence >= 0 and confidence <= 1),

    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),

    check (
        source_observation_id <> target_observation_id
    ),

    unique (
        source_observation_id,
        target_observation_id,
        relationship_type
    )
);

-- ============================================================
-- HISTORY
-- ============================================================

create table if not exists intelligence_observation_history (
    id uuid primary key default gen_random_uuid(),

    observation_id uuid not null
        references intelligence_observations(id)
        on delete cascade,

    change_type text not null,
    previous_state jsonb,
    current_state jsonb not null,

    changed_at timestamptz not null default now(),
    changed_by text default 'SYSTEM'
);

-- ============================================================
-- INDEXES
-- ============================================================

create index if not exists idx_intel_obs_country
    on intelligence_observations(country_iso3);

create index if not exists idx_intel_obs_region
    on intelligence_observations(region_key);

create index if not exists idx_intel_obs_source
    on intelligence_observations(source_key);

create index if not exists idx_intel_obs_type
    on intelligence_observations(observation_type);

create index if not exists idx_intel_obs_material
    on intelligence_observations(is_material, materiality_score desc);

create index if not exists idx_intel_obs_effective
    on intelligence_observations(effective_at desc);

create index if not exists idx_intel_obs_status
    on intelligence_observations(status);

create index if not exists idx_intel_obs_indicator_key
    on intelligence_observation_indicators(indicator_key);

create index if not exists idx_intel_obs_entity_name
    on intelligence_observation_entities(entity_name);

create index if not exists idx_intel_obs_entity_kg
    on intelligence_observation_entities(
        knowledge_graph_entity_id
    );

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================

create or replace function set_intelligence_observation_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_intelligence_observation_updated_at
on intelligence_observations;

create trigger trg_intelligence_observation_updated_at
before update on intelligence_observations
for each row
execute function set_intelligence_observation_updated_at();

-- ============================================================
-- HISTORY TRIGGER
-- ============================================================

create or replace function record_intelligence_observation_history()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'INSERT' then
        insert into intelligence_observation_history (
            observation_id,
            change_type,
            previous_state,
            current_state
        )
        values (
            new.id,
            'CREATED',
            null,
            to_jsonb(new)
        );

        return new;
    end if;

    if tg_op = 'UPDATE' then
        insert into intelligence_observation_history (
            observation_id,
            change_type,
            previous_state,
            current_state
        )
        values (
            new.id,
            'UPDATED',
            to_jsonb(old),
            to_jsonb(new)
        );

        return new;
    end if;

    return new;
end;
$$;

drop trigger if exists trg_intelligence_observation_history
on intelligence_observations;

create trigger trg_intelligence_observation_history
after insert or update on intelligence_observations
for each row
execute function record_intelligence_observation_history();

-- ============================================================
-- MATERIAL OBSERVATIONS VIEW
-- ============================================================

create or replace view intelligence_material_observations as
select
    observation.*,
    coalesce(indicator_summary.indicator_count, 0)
        as indicator_count,
    coalesce(entity_summary.entity_count, 0)
        as entity_count
from intelligence_observations observation
left join (
    select
        observation_id,
        count(*) as indicator_count
    from intelligence_observation_indicators
    group by observation_id
) indicator_summary
    on indicator_summary.observation_id = observation.id
left join (
    select
        observation_id,
        count(*) as entity_count
    from intelligence_observation_entities
    group by observation_id
) entity_summary
    on entity_summary.observation_id = observation.id
where
    observation.is_material = true
    and observation.status = 'ACTIVE';

-- ============================================================
-- ROW LEVEL SECURITY
-- Backend service-role access remains unaffected.
-- ============================================================

alter table intelligence_observations
    enable row level security;

alter table intelligence_observation_entities
    enable row level security;

alter table intelligence_observation_indicators
    enable row level security;

alter table intelligence_observation_relationships
    enable row level security;

alter table intelligence_observation_history
    enable row level security;

commit;
