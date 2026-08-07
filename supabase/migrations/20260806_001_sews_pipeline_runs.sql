-- SEWS Phase 6.6: auditable production pipeline runs
create table if not exists public.sews_pipeline_runs (
    id uuid primary key default gen_random_uuid(),
    run_key text not null unique,
    mode text not null default 'ONCE',
    status text not null default 'RUNNING',
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    duration_seconds numeric,
    source_keys jsonb not null default '[]'::jsonb,
    stages jsonb not null default '[]'::jsonb,
    warnings_updated integer not null default 0,
    indicators_updated integer not null default 0,
    evidence_records integer not null default 0,
    propagation_events integer not null default 0,
    products_generated integer not null default 0,
    errors jsonb not null default '[]'::jsonb,
    pipeline_version text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_sews_pipeline_runs_started_at
    on public.sews_pipeline_runs (started_at desc);

create index if not exists idx_sews_pipeline_runs_status
    on public.sews_pipeline_runs (status);

alter table public.sews_pipeline_runs enable row level security;

comment on table public.sews_pipeline_runs is
'Auditable execution ledger for the unified SEWS production pipeline.';
