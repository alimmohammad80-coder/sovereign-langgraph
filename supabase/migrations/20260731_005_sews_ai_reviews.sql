begin;

create table if not exists sews_ai_reviews (
    id uuid primary key default gen_random_uuid(),

    warning_problem_id uuid not null
        references sews_warning_problems(id)
        on delete cascade,

    assessment_id uuid not null
        references sews_assessments(id)
        on delete cascade,

    reviewed_at timestamptz not null default now(),

    model_provider text not null,
    model_name text not null,

    official_probability numeric not null
        check (official_probability between 0 and 1),

    official_confidence numeric not null
        check (official_confidence between 0 and 1),

    suggested_probability numeric not null
        check (suggested_probability between 0 and 1),

    suggested_confidence numeric not null
        check (suggested_confidence between 0 and 1),

    probability_variance numeric not null,
    confidence_variance numeric not null,

    agreement_score numeric not null
        check (agreement_score between 0 and 1),

    disposition text not null
        check (
            disposition in (
                'AGREE',
                'MINOR_DISAGREEMENT',
                'MAJOR_DISAGREEMENT',
                'CRITICAL_DIVERGENCE'
            )
        ),

    recommended_state sews_problem_state not null,
    maintain_official_state boolean not null,

    key_drivers jsonb not null default '[]'::jsonb,
    contrary_evidence jsonb not null default '[]'::jsonb,
    confidence_rationale text not null,
    monitoring_priorities jsonb not null default '[]'::jsonb,
    historical_analogs jsonb not null default '[]'::jsonb,
    narrative text not null,
    raw_model_output jsonb not null,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (
        assessment_id,
        model_provider,
        model_name
    )
);

create index if not exists idx_sews_ai_reviews_problem
    on sews_ai_reviews(
        warning_problem_id,
        reviewed_at desc
    );

create index if not exists idx_sews_ai_reviews_assessment
    on sews_ai_reviews(assessment_id);

create index if not exists idx_sews_ai_reviews_disposition
    on sews_ai_reviews(disposition);

create index if not exists idx_sews_ai_reviews_variance
    on sews_ai_reviews(
        abs(probability_variance) desc
    );

drop trigger if exists trg_sews_ai_reviews_updated_at
    on sews_ai_reviews;

create trigger trg_sews_ai_reviews_updated_at
before update on sews_ai_reviews
for each row execute function sews_set_updated_at();

alter table sews_ai_reviews enable row level security;

drop policy if exists "authenticated read ai reviews"
    on sews_ai_reviews;

create policy "authenticated read ai reviews"
on sews_ai_reviews
for select
to authenticated
using (true);

commit;
