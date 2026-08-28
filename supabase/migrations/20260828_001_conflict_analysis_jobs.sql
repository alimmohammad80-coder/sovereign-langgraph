create table if not exists public.conflict_analysis_jobs (
    id uuid primary key default gen_random_uuid(),

    conflict_id integer not null,

    horizon_days integer not null default 365,
    lookback_days integer not null default 90,
    ripple_depth integer not null default 3,

    preferred_provider text,
    preferred_model text,

    status text not null default 'queued'
        check (
            status in (
                'queued',
                'processing',
                'completed',
                'failed'
            )
        ),

    provider text,
    model text,

    result jsonb,
    qa jsonb,
    error_message text,

    created_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz not null default now()
);

create index if not exists
    conflict_analysis_jobs_conflict_id_idx
on public.conflict_analysis_jobs(conflict_id);

create index if not exists
    conflict_analysis_jobs_status_idx
on public.conflict_analysis_jobs(status);

create index if not exists
    conflict_analysis_jobs_created_at_idx
on public.conflict_analysis_jobs(created_at desc);
