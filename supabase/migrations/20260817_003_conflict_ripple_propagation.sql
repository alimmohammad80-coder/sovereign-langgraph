create table if not exists public.conflict_propagation_edges (

    id uuid primary key default gen_random_uuid(),

    edge_key text not null unique,

    source_node text not null,
    source_type text not null,

    target_node text not null,
    target_type text not null,

    channel text not null,

    transmission_weight numeric not null
        check (
            transmission_weight >= 0
            and transmission_weight <= 1
        ),

    damping_factor numeric not null default 1.0
        check (
            damping_factor >= 0
            and damping_factor <= 1
        ),

    confidence numeric
        check (
            confidence is null
            or (
                confidence >= 0
                and confidence <= 100
            )
        ),

    method text not null default 'deterministic',

    source text,
    source_version text,

    active boolean not null default true,

    review_status text not null default 'validated',

    last_reviewed date,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists
idx_conflict_propagation_edges_source
on public.conflict_propagation_edges(
    source_node,
    channel
)
where active = true;

create index if not exists
idx_conflict_propagation_edges_target
on public.conflict_propagation_edges(
    target_node,
    channel
)
where active = true;


create table if not exists public.conflict_ripple_runs (

    id uuid primary key default gen_random_uuid(),

    run_key text not null unique,

    conflict_id integer not null,

    canonical_episode_id uuid,

    generated_at timestamptz not null default now(),

    horizon_days integer not null,

    forecast_probability numeric not null
        check (
            forecast_probability >= 0
            and forecast_probability <= 1
        ),

    calibrated_probability numeric
        check (
            calibrated_probability is null
            or (
                calibrated_probability >= 0
                and calibrated_probability <= 1
            )
        ),

    propagation_depth integer not null default 2,

    channel_impacts jsonb not null default '{}'::jsonb,

    affected_nodes jsonb not null default '[]'::jsonb,

    propagation_paths jsonb not null default '[]'::jsonb,

    model_version text not null,

    active boolean not null default true,

    review_status text not null default 'validated',

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists
idx_conflict_ripple_runs_latest
on public.conflict_ripple_runs(
    conflict_id,
    generated_at desc
);

notify pgrst, 'reload schema';
