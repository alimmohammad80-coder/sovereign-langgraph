create table if not exists sews_warning_baselines (
    id uuid primary key default gen_random_uuid(),

    warning_problem_id uuid not null
        references sews_warning_problems(id)
        on delete cascade,

    strategic_context text not null,
    why_it_matters text not null,

    structural_drivers jsonb not null default '[]'::jsonb,
    escalation_pathways jsonb not null default '[]'::jsonb,
    historical_analogs jsonb not null default '[]'::jsonb,
    monitoring_priorities jsonb not null default '[]'::jsonb,

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (warning_problem_id)
);

create index if not exists idx_sews_warning_baselines_problem
on sews_warning_baselines(warning_problem_id);

alter table sews_warning_baselines enable row level security;

create policy "authenticated read warning baselines"
on sews_warning_baselines
for select
to authenticated
using (true);
