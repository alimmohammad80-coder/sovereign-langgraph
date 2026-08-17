begin;

create extension if not exists pgcrypto;
create extension if not exists postgis;

do $$ begin
  create type conflict_review_status as enum ('validated','provisional','requires_review','rejected');
exception when duplicate_object then null; end $$;

do $$ begin
  create type conflict_confidence_grade as enum ('high','medium','low','unknown');
exception when duplicate_object then null; end $$;

do $$ begin
  create type conflict_state_code as enum (
    'S0_STABLE','S1_TENSION','S2_CRISIS','S3_LIMITED_CONFLICT','S4_WAR','S5_FROZEN'
  );
exception when duplicate_object then null; end $$;

create table if not exists conflict_countries (
  id uuid primary key default gen_random_uuid(),
  iso3 text not null unique check (char_length(iso3)=3),
  iso2 text unique check (iso2 is null or char_length(iso2)=2),
  name text not null,
  official_name text,
  region text,
  subregion text,
  income_group text,
  regime_type text,
  capital text,
  latitude double precision check (latitude is null or latitude between -90 and 90),
  longitude double precision check (longitude is null or longitude between -180 and 180),
  geometry geography(multipolygon,4326),
  geometry_ref text,
  active boolean not null default true,
  source text not null,
  source_version text,
  confidence_grade conflict_confidence_grade not null default 'unknown',
  review_status conflict_review_status not null default 'requires_review',
  last_reviewed date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists conflict_border_dyads (
  id uuid primary key default gen_random_uuid(),
  dyad_id text not null unique,
  country_a_iso3 text not null references conflict_countries(iso3),
  country_b_iso3 text not null references conflict_countries(iso3),
  dyad_type text not null check (dyad_type in ('land','maritime','eez','mixed')),
  border_length_km numeric check (border_length_km is null or border_length_km >= 0),
  disputed_flag boolean not null default false,
  dispute_name text,
  dispute_ref text,
  militarization_index numeric check (militarization_index is null or militarization_index between 0 and 100),
  trade_interdependence numeric check (trade_interdependence is null or trade_interdependence between 0 and 1),
  alliance_overlap numeric check (alliance_overlap is null or alliance_overlap between 0 and 1),
  geometry geography(multilinestring,4326),
  geometry_ref text,
  active boolean not null default true,
  source text not null,
  source_version text,
  confidence_grade conflict_confidence_grade not null default 'unknown',
  review_status conflict_review_status not null default 'requires_review',
  last_reviewed date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (country_a_iso3 < country_b_iso3),
  check (dyad_id = 'DYAD-' || country_a_iso3 || '-' || country_b_iso3 || '-' || upper(dyad_type)),
  unique(country_a_iso3, country_b_iso3, dyad_type)
);

create table if not exists conflict_territories (
  id uuid primary key default gen_random_uuid(),
  territory_id text not null unique,
  name text not null,
  de_jure_iso3 text references conflict_countries(iso3),
  de_facto_controller text,
  status text not null check (status in ('contested','occupied','autonomous','frozen_entity','disputed','unresolved')),
  claimants jsonb not null default '[]'::jsonb,
  geometry geography(multipolygon,4326),
  geometry_ref text,
  active boolean not null default true,
  source text not null,
  source_version text,
  confidence_grade conflict_confidence_grade not null default 'unknown',
  review_status conflict_review_status not null default 'requires_review',
  last_reviewed date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists conflict_frozen_conflicts (
  id uuid primary key default gen_random_uuid(),
  fc_id text not null unique,
  name text not null,
  parties jsonb not null default '[]'::jsonb,
  territory_id text references conflict_territories(territory_id),
  primary_dyad_id text references conflict_border_dyads(dyad_id),
  freeze_year integer check (freeze_year is null or freeze_year between 1900 and 2100),
  last_flare_date date,
  mediation_regime text,
  peacekeeping_presence boolean,
  current_status text not null,
  reactivation_hazard_score numeric check (
    reactivation_hazard_score is null or reactivation_hazard_score between 0 and 100
  ),
  hazard_confidence conflict_confidence_grade not null default 'unknown',
  window_watch boolean not null default false,
  active boolean not null default true,
  source text not null,
  source_version text,
  review_status conflict_review_status not null default 'requires_review',
  last_reviewed date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists conflict_armed_actors (
  id uuid primary key default gen_random_uuid(),
  actor_id text not null unique,
  name text not null,
  actor_type text not null check (actor_type in (
    'state','rebel','militia','political_armed_group','jihadist',
    'cartel','private_military_company','separatist','unknown'
  )),
  aliases jsonb not null default '[]'::jsonb,
  state_sponsor_iso3 jsonb not null default '[]'::jsonb,
  estimated_strength integer check (estimated_strength is null or estimated_strength >= 0),
  areas_of_operation geography(multipolygon,4326),
  areas_of_operation_ref text,
  acled_actor_ids jsonb not null default '[]'::jsonb,
  ucdp_actor_ids jsonb not null default '[]'::jsonb,
  active_from date,
  active_to date,
  active boolean not null default true,
  source text not null,
  source_version text,
  confidence_grade conflict_confidence_grade not null default 'unknown',
  review_status conflict_review_status not null default 'requires_review',
  last_reviewed date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists conflict_episodes (
  id uuid primary key default gen_random_uuid(),
  episode_id text not null unique,
  external_ids jsonb not null default '{}'::jsonb,
  name text not null,
  parties jsonb not null default '[]'::jsonb,
  onset_date date,
  termination_date date,
  conflict_type text not null check (conflict_type in (
    'interstate','intrastate','internationalized_intrastate','one_sided','non_state','territorial'
  )),
  status text not null check (status in ('active','frozen','terminated','latent','unknown')),
  affected_countries jsonb not null default '[]'::jsonb,
  territories jsonb not null default '[]'::jsonb,
  peak_state conflict_state_code,
  source text not null,
  source_version text,
  confidence_grade conflict_confidence_grade not null default 'unknown',
  review_status conflict_review_status not null default 'requires_review',
  last_reviewed date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists conflict_state_history (
  id uuid primary key default gen_random_uuid(),
  unit_id text not null,
  unit_type text not null check (unit_type in ('country','dyad','territory','frozen_conflict','episode')),
  observed_at timestamptz not null,
  conflict_state conflict_state_code not null,
  severity_tier text not null check (severity_tier in ('Minimal','Guarded','Elevated','High','Critical')),
  source text not null,
  source_version text,
  evidence_refs jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  unique(unit_id, unit_type, observed_at)
);

create table if not exists conflict_observations (
  id uuid primary key default gen_random_uuid(),
  unit_id text not null,
  unit_type text not null,
  observed_at timestamptz not null,
  indicator_key text,
  value_numeric numeric,
  value_text text,
  value_json jsonb,
  source text not null,
  source_url text,
  source_version text,
  confidence_grade conflict_confidence_grade not null default 'unknown',
  review_status conflict_review_status not null default 'requires_review',
  created_at timestamptz not null default now()
);

create table if not exists conflict_evidence (
  id uuid primary key default gen_random_uuid(),
  observation_id uuid references conflict_observations(id) on delete set null,
  title text not null,
  excerpt text,
  source text not null,
  source_url text,
  published_at timestamptz,
  retrieved_at timestamptz not null default now(),
  content_hash text,
  confidence_grade conflict_confidence_grade not null default 'unknown',
  review_status conflict_review_status not null default 'requires_review',
  created_at timestamptz not null default now()
);

create table if not exists conflict_assessments (
  id uuid primary key default gen_random_uuid(),
  unit_id text not null,
  unit_type text not null,
  as_of timestamptz not null,
  conflict_state conflict_state_code not null,
  severity_tier text not null check (severity_tier in ('Minimal','Guarded','Elevated','High','Critical')),
  confidence_score numeric check (confidence_score is null or confidence_score between 0 and 100),
  indicator_snapshot jsonb not null default '{}'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  formula_version text not null,
  parameter_version text not null,
  data_snapshot_id text not null,
  created_at timestamptz not null default now(),
  unique(unit_id, unit_type, as_of, formula_version, parameter_version, data_snapshot_id)
);

create table if not exists conflict_parameters (
  id uuid primary key default gen_random_uuid(),
  parameter_version text not null unique,
  parameters jsonb not null,
  content_hash text not null,
  active boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists conflict_snapshots (
  id uuid primary key default gen_random_uuid(),
  snapshot_id text not null unique,
  source_versions jsonb not null,
  record_counts jsonb not null,
  content_hash text not null,
  status text not null check (status in ('building','ready','failed','superseded')),
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_conflict_countries_region on conflict_countries(region, subregion);
create index if not exists idx_conflict_dyads_members on conflict_border_dyads(country_a_iso3, country_b_iso3);
create index if not exists idx_conflict_dyads_disputed on conflict_border_dyads(disputed_flag);
create index if not exists idx_conflict_territories_status on conflict_territories(status);
create index if not exists idx_conflict_frozen_watch on conflict_frozen_conflicts(window_watch);
create index if not exists idx_conflict_actors_type on conflict_armed_actors(actor_type);
create index if not exists idx_conflict_episodes_status on conflict_episodes(status);
create index if not exists idx_conflict_state_unit on conflict_state_history(unit_type, unit_id, observed_at desc);
create index if not exists idx_conflict_observations_unit on conflict_observations(unit_type, unit_id, observed_at desc);
create index if not exists idx_conflict_assessments_unit on conflict_assessments(unit_type, unit_id, as_of desc);

alter table conflict_countries enable row level security;
alter table conflict_border_dyads enable row level security;
alter table conflict_territories enable row level security;
alter table conflict_frozen_conflicts enable row level security;
alter table conflict_armed_actors enable row level security;
alter table conflict_episodes enable row level security;
alter table conflict_state_history enable row level security;
alter table conflict_observations enable row level security;
alter table conflict_evidence enable row level security;
alter table conflict_assessments enable row level security;
alter table conflict_parameters enable row level security;
alter table conflict_snapshots enable row level security;

commit;
