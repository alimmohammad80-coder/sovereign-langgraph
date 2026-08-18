create table if not exists public.conflict_forecasts (

    id uuid primary key default gen_random_uuid(),
    run_key text not null unique,
    conflict_id integer not null,
    canonical_episode_id uuid,
    generated_at timestamptz not null default now(),
    horizon_days integer not null,
    lookback_days integer not null,
    current_state text not null,

    ensemble_probability numeric not null
        check (
            ensemble_probability >= 0
            and ensemble_probability <= 1
        ),

    risk_band text not null,
    confidence numeric,

    component_probabilities jsonb not null default '{}'::jsonb,
    model_applicability jsonb not null default '{}'::jsonb,
    normalized_weights jsonb not null default '{}'::jsonb,
    state_forecast_distribution jsonb not null default '{}'::jsonb,
    primary_evidence jsonb not null default '[]'::jsonb,

    frozen_conflict_id text,

    model_versions jsonb not null default '{}'::jsonb,
    ensemble_model text not null,

    outcome_state text,
    outcome_observed_at timestamptz,
    outcome_event_occurred boolean,

    calibrated_probability numeric,
    calibration_version text,

    active boolean not null default true,
    review_status text not null default 'validated',

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists
idx_conflict_forecasts_latest
on public.conflict_forecasts(
    conflict_id,
    horizon_days,
    generated_at desc
);

create index if not exists
idx_conflict_forecasts_outcomes
on public.conflict_forecasts(
    horizon_days,
    outcome_observed_at
)
where outcome_observed_at is not null;
