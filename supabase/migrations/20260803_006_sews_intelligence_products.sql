create table if not exists sews_intelligence_products (
    id uuid primary key default gen_random_uuid(),
    warning_problem_key text not null,
    causal_assessment_id uuid references sews_causal_assessments(id) on delete set null,
    warning_assessment_id uuid references sews_assessments(id) on delete set null,
    country_iso3 char(3),
    region_key text,
    generated_at timestamptz not null default now(),
    probability numeric(8,6) check (probability is null or probability between 0 and 1),
    confidence numeric(5,2) check (confidence is null or confidence between 0 and 100),
    trend text,
    bluf text not null,
    executive_summary text not null,
    complete_analysis text not null,
    key_drivers jsonb not null default '[]'::jsonb,
    confidence_explanation jsonb not null default '{}'::jsonb,
    evidence_summary jsonb not null default '[]'::jsonb,
    forecast jsonb not null default '{}'::jsonb,
    scenarios jsonb not null default '[]'::jsonb,
    intelligence_gaps jsonb not null default '[]'::jsonb,
    collection_priorities jsonb not null default '[]'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_sews_intelligence_products_problem
    on sews_intelligence_products(warning_problem_key, generated_at desc);

create index if not exists idx_sews_intelligence_products_causal
    on sews_intelligence_products(causal_assessment_id);

create unique index if not exists uq_sews_intelligence_product_causal
    on sews_intelligence_products(warning_problem_key, causal_assessment_id)
    where causal_assessment_id is not null;

create or replace view sews_latest_intelligence_products as
select distinct on (warning_problem_key) *
from sews_intelligence_products
order by warning_problem_key, generated_at desc;
