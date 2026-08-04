create table if not exists public.sews_causal_nodes (
    id uuid primary key default gen_random_uuid(),
    node_key text not null unique,
    problem_key text not null,
    name text not null,
    description text,
    node_type text not null
        check (node_type in (
            'CONDITION',
            'ACTION',
            'EVENT',
            'INTERMEDIATE_EFFECT',
            'OUTCOME',
            'MITIGATOR'
        )),
    prior_probability numeric(8,6) not null default 0.1
        check (prior_probability between 0 and 1),
    current_probability numeric(8,6)
        check (
            current_probability is null
            or current_probability between 0 and 1
        ),
    confidence numeric(5,2) not null default 0
        check (confidence between 0 and 100),
    decay_half_life_hours integer not null default 168
        check (decay_half_life_hours > 0),
    sequence_order integer not null default 0,
    active boolean not null default true,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.sews_causal_edges (
    id uuid primary key default gen_random_uuid(),
    edge_key text not null unique,
    problem_key text not null,
    parent_node_id uuid not null
        references public.sews_causal_nodes(id) on delete cascade,
    child_node_id uuid not null
        references public.sews_causal_nodes(id) on delete cascade,
    relationship_type text not null
        check (relationship_type in (
            'ENABLES',
            'INCREASES',
            'TRIGGERS',
            'TRANSMITS',
            'MITIGATES',
            'INHIBITS'
        )),
    transmission_strength numeric(8,6) not null
        check (transmission_strength between 0 and 1),
    conditional_probability numeric(8,6) not null
        check (conditional_probability between 0 and 1),
    lag_hours integer not null default 0
        check (lag_hours >= 0),
    capacity_limit numeric(8,6)
        check (
            capacity_limit is null
            or capacity_limit between 0 and 1
        ),
    active boolean not null default true,
    rationale text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    constraint sews_causal_edges_no_self_loop
        check (parent_node_id <> child_node_id),
    unique (problem_key, parent_node_id, child_node_id)
);

create table if not exists public.sews_causal_node_indicator_links (
    id uuid primary key default gen_random_uuid(),
    node_id uuid not null
        references public.sews_causal_nodes(id) on delete cascade,
    indicator_key text not null,
    influence_type text not null
        check (influence_type in (
            'SUPPORTING',
            'CONTRADICTING'
        )),
    influence_weight numeric(8,6) not null default 1
        check (influence_weight between 0 and 10),
    active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (node_id, indicator_key, influence_type)
);

create table if not exists public.sews_causal_assessments (
    id uuid primary key default gen_random_uuid(),
    problem_key text not null,
    warning_assessment_id uuid
        references public.sews_assessments(id) on delete set null,
    assessed_at timestamptz not null default now(),
    root_probability numeric(8,6) not null
        check (root_probability between 0 and 1),
    outcome_probability numeric(8,6) not null
        check (outcome_probability between 0 and 1),
    confidence_score numeric(5,2) not null
        check (confidence_score between 0 and 100),
    node_snapshot jsonb not null default '[]'::jsonb,
    edge_snapshot jsonb not null default '[]'::jsonb,
    explanation jsonb not null default '{}'::jsonb,
    formula_version text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_sews_causal_nodes_problem
    on public.sews_causal_nodes(problem_key, sequence_order);

create index if not exists idx_sews_causal_edges_problem
    on public.sews_causal_edges(problem_key);

create index if not exists idx_sews_causal_links_node
    on public.sews_causal_node_indicator_links(node_id);

create index if not exists idx_sews_causal_assessments_problem
    on public.sews_causal_assessments(problem_key, assessed_at desc);
