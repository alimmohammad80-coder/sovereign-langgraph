create table if not exists public.supply_chain_analysis_jobs (
    id uuid primary key default gen_random_uuid(),

    entity_type text not null,
    entity_name text not null,
    request_json jsonb not null,

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
    supply_chain_analysis_jobs_entity_idx
on public.supply_chain_analysis_jobs(
    entity_type,
    lower(entity_name),
    created_at desc
);

create index if not exists
    supply_chain_analysis_jobs_status_idx
on public.supply_chain_analysis_jobs(status);

create index if not exists
    supply_chain_analysis_jobs_created_at_idx
on public.supply_chain_analysis_jobs(created_at desc);
