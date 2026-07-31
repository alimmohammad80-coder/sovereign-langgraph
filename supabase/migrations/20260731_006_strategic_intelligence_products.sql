begin;

create table if not exists strategic_intelligence_products (
    id uuid primary key default gen_random_uuid(),

    product_key text not null unique,
    product_type text not null,

    warning_problem_id uuid not null
        references sews_warning_problems(id)
        on delete cascade,

    assessment_id uuid not null
        references sews_assessments(id)
        on delete cascade,

    ai_review_id uuid
        references sews_ai_reviews(id)
        on delete set null,

    title text not null,
    bluf text not null,
    executive_summary text not null,

    official_assessment jsonb not null,
    ai_strategic_review jsonb,

    drivers jsonb not null default '[]'::jsonb,
    contrary_evidence jsonb not null default '[]'::jsonb,
    confidence_and_provenance jsonb not null,
    historical_analogs jsonb not null default '[]'::jsonb,
    monitoring_priorities jsonb not null default '[]'::jsonb,
    forecast jsonb not null default '{}'::jsonb,

    full_analysis text not null,
    quality_assurance jsonb not null,
    publication jsonb not null default '{}'::jsonb,

    published_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (
        assessment_id,
        product_type
    )
);

create index if not exists idx_sip_problem_time
    on strategic_intelligence_products(
        warning_problem_id,
        created_at desc
    );

create index if not exists idx_sip_assessment
    on strategic_intelligence_products(assessment_id);

create index if not exists idx_sip_published
    on strategic_intelligence_products(published_at desc);

create index if not exists idx_sip_publication
    on strategic_intelligence_products
    using gin(publication);

create index if not exists idx_sip_provenance
    on strategic_intelligence_products
    using gin(confidence_and_provenance);

drop trigger if exists trg_sip_updated_at
    on strategic_intelligence_products;

create trigger trg_sip_updated_at
before update on strategic_intelligence_products
for each row execute function sews_set_updated_at();

alter table strategic_intelligence_products
    enable row level security;

drop policy if exists "authenticated read strategic products"
    on strategic_intelligence_products;

create policy "authenticated read strategic products"
on strategic_intelligence_products
for select
to authenticated
using (true);

commit;
