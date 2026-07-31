-- SEWS Phase 1 core schema
create extension if not exists pgcrypto;

create type sews_problem_state as enum (
  'DORMANT','WATCH','ADVISORY','WARNING','CRITICAL','RESOLVED','FALSIFIED'
);

create type sews_indicator_class as enum (
  'PRECURSOR','ACCELERANT','TRIGGER','CONTRA'
);

create type sews_indicator_status as enum (
  'QUIET','STIRRING','ACTIVE','CONTRADICTING','DARK'
);

create table if not exists sews_warning_problems (
  id uuid primary key default gen_random_uuid(),
  problem_key text unique not null,
  title text not null,
  hypothesis text not null,
  horizon_days integer not null check (horizon_days > 0),
  state sews_problem_state not null default 'DORMANT',
  base_rate numeric not null check (base_rate > 0 and base_rate < 1),
  severity_score numeric not null default 0 check (severity_score between 0 and 100),
  version integer not null default 1,
  active boolean not null default true,
  exposure_map jsonb not null default '{}'::jsonb,
  transition_rules jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists sews_indicators (
  id uuid primary key default gen_random_uuid(),
  warning_problem_id uuid not null references sews_warning_problems(id) on delete cascade,
  indicator_key text not null,
  description text not null,
  source_module text not null,
  source_series text not null,
  class sews_indicator_class not null,
  polarity smallint not null check (polarity in (-1, 1)),
  threshold_definition jsonb not null,
  weight numeric not null check (weight between 0 and 5),
  weight_floor numeric not null default 0,
  weight_cap numeric not null default 5,
  decay_half_life_days numeric not null default 21 check (decay_half_life_days > 0),
  status sews_indicator_status not null default 'QUIET',
  current_value numeric,
  baseline_z numeric,
  last_observed_at timestamptz,
  dark_after_hours integer not null default 72,
  metadata jsonb not null default '{}'::jsonb,
  unique (warning_problem_id, indicator_key)
);

create table if not exists sews_signals (
  id uuid primary key default gen_random_uuid(),
  signal_key text unique not null,
  observed_at timestamptz not null,
  ingested_at timestamptz not null default now(),
  entity_ids jsonb not null default '[]'::jsonb,
  domain text not null,
  signal_type text not null,
  value numeric,
  baseline_z numeric,
  source_chain jsonb not null,
  source_reliability text not null,
  information_credibility integer not null check (information_credibility between 1 and 6),
  latency_class text not null check (latency_class in ('FLASH','PRIORITY','ROUTINE')),
  linked_indicators jsonb not null default '[]'::jsonb,
  raw_payload jsonb not null default '{}'::jsonb
);

create table if not exists sews_assessments (
  id uuid primary key default gen_random_uuid(),
  warning_problem_id uuid not null references sews_warning_problems(id) on delete cascade,
  assessed_at timestamptz not null default now(),
  probability numeric not null check (probability between 0 and 1),
  probability_band text not null,
  confidence_score numeric not null check (confidence_score between 0 and 100),
  confidence_level text not null check (confidence_level in ('LOW','MEDIUM','HIGH')),
  severity_score numeric not null check (severity_score between 0 and 100),
  recommended_state sews_problem_state not null,
  indicator_snapshot jsonb not null,
  confidence_breakdown jsonb not null,
  formula_version text not null,
  deterministic_payload jsonb not null
);

create table if not exists sews_state_transitions (
  id uuid primary key default gen_random_uuid(),
  warning_problem_id uuid not null references sews_warning_problems(id) on delete cascade,
  from_state sews_problem_state not null,
  to_state sews_problem_state not null,
  assessment_id uuid references sews_assessments(id),
  reason text not null,
  actor_type text not null check (actor_type in ('SYSTEM','ANALYST')),
  actor_id text,
  created_at timestamptz not null default now()
);

create table if not exists sews_warning_ledger (
  id uuid primary key default gen_random_uuid(),
  warning_problem_id uuid not null references sews_warning_problems(id) on delete cascade,
  ledger_number text unique not null,
  version integer not null,
  assessment_id uuid not null references sews_assessments(id),
  state sews_problem_state not null,
  deterministic_header jsonb not null,
  narrative_body jsonb,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  unique (warning_problem_id, version)
);

create index if not exists idx_sews_signals_observed_at on sews_signals(observed_at desc);
create index if not exists idx_sews_indicators_problem on sews_indicators(warning_problem_id);
create index if not exists idx_sews_assessments_problem_time on sews_assessments(warning_problem_id, assessed_at desc);
create index if not exists idx_sews_transitions_problem_time on sews_state_transitions(warning_problem_id, created_at desc);

alter table sews_warning_problems enable row level security;
alter table sews_indicators enable row level security;
alter table sews_signals enable row level security;
alter table sews_assessments enable row level security;
alter table sews_state_transitions enable row level security;
alter table sews_warning_ledger enable row level security;

-- Replace these permissive authenticated-read policies with organization-aware policies
-- when tenant/org tables are connected.
create policy "authenticated read warning problems"
on sews_warning_problems for select to authenticated using (true);

create policy "authenticated read indicators"
on sews_indicators for select to authenticated using (true);

create policy "authenticated read assessments"
on sews_assessments for select to authenticated using (true);

create policy "authenticated read transitions"
on sews_state_transitions for select to authenticated using (true);

create policy "authenticated read ledger"
on sews_warning_ledger for select to authenticated using (true);
