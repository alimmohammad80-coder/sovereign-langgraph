-- Optimize the SEWS operational dashboard product query.
-- Preserve full intelligence-product history while exposing only
-- the latest operational fields for each warning problem.

create index if not exists
    idx_sews_intelligence_products_latest_problem
on public.sews_intelligence_products (
    warning_problem_key,
    generated_at desc
);

create or replace view
    public.sews_latest_operational_products
with (security_invoker = true)
as
select distinct on (warning_problem_key)
    id,
    warning_problem_key,
    generated_at,
    confidence,
    confidence_status,
    raw_confidence,
    trend,
    bluf,
    key_drivers,
    forecast,
    intelligence_gaps,
    collection_priorities
from public.sews_intelligence_products
where warning_problem_key is not null
order by
    warning_problem_key,
    generated_at desc;

grant select
on public.sews_latest_operational_products
to service_role;
