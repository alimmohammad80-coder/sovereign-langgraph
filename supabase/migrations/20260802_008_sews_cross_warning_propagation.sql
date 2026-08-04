create table if not exists public.sews_cross_warning_propagation_runs (
    id uuid primary key default gen_random_uuid(),
    dependency_id uuid not null
        references public.sews_warning_dependencies(id)
        on delete cascade,
    dependency_key text not null,
    source_problem_key text not null,
    target_problem_key text not null,
    relationship_type text not null,
    source_probability numeric(8,6) not null
        check (source_probability between 0 and 1),
    target_probability_before numeric(8,6) not null
        check (target_probability_before between 0 and 1),
    transmitted_effect numeric(8,6) not null
        check (transmitted_effect between 0 and 1),
    target_probability_after numeric(8,6) not null
        check (target_probability_after between 0 and 1),
    transmission_strength numeric(8,6) not null
        check (transmission_strength between 0 and 1),
    conditional_probability numeric(8,6) not null
        check (conditional_probability between 0 and 1),
    lag_hours integer not null default 0,
    formula_version text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_sews_cross_warning_runs_source
    on public.sews_cross_warning_propagation_runs(
        source_problem_key,
        created_at desc
    );

create index if not exists idx_sews_cross_warning_runs_target
    on public.sews_cross_warning_propagation_runs(
        target_problem_key,
        created_at desc
    );

notify pgrst, 'reload schema';
