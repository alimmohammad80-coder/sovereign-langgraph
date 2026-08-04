create table if not exists public.sews_warning_dependencies (
    id uuid primary key default gen_random_uuid(),
    dependency_key text not null unique,
    source_problem_key text not null,
    target_problem_key text not null,
    relationship_type text not null
        check (relationship_type in (
            'RELATED',
            'CAUSES',
            'AMPLIFIES',
            'TRANSMITS',
            'MITIGATES',
            'INHIBITS'
        )),
    direction_status text not null default 'UNVALIDATED'
        check (direction_status in (
            'UNVALIDATED',
            'VALIDATED',
            'REJECTED'
        )),
    transmission_strength numeric(8,6) not null default 0
        check (transmission_strength between 0 and 1),
    conditional_probability numeric(8,6)
        check (
            conditional_probability is null
            or conditional_probability between 0 and 1
        ),
    lag_hours integer not null default 0
        check (lag_hours >= 0),
    rationale text,
    active boolean not null default true,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint sews_warning_dependencies_no_self
        check (source_problem_key <> target_problem_key)
);

create index if not exists idx_sews_warning_dependencies_source
    on public.sews_warning_dependencies(source_problem_key);

create index if not exists idx_sews_warning_dependencies_target
    on public.sews_warning_dependencies(target_problem_key);

create index if not exists idx_sews_warning_dependencies_type
    on public.sews_warning_dependencies(relationship_type);

notify pgrst, 'reload schema';
