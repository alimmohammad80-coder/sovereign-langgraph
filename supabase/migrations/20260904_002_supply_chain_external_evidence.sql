create table if not exists public.sc_external_evidence (
    id uuid primary key default gen_random_uuid(),
    source text not null,
    source_record_id text not null,
    evidence_type text not null,
    title text not null,
    summary text not null default '',
    url text,
    published_at timestamptz,
    observed_at timestamptz,
    country_iso3 text,
    matched_company text,
    matched_port text,
    matched_chokepoint text,
    matched_commodity text,
    matched_corridor text,
    event_type text,
    severity_score double precision,
    confidence_score double precision,
    metric_name text,
    metric_value double precision,
    metric_unit text,
    raw_payload jsonb not null default '{}'::jsonb,
    content_hash text not null,
    ingested_at timestamptz not null default now(),
    unique (source, source_record_id)
);

create index if not exists sc_external_evidence_published_idx
on public.sc_external_evidence(published_at desc);

create index if not exists sc_external_evidence_company_idx
on public.sc_external_evidence(lower(matched_company), published_at desc);

create index if not exists sc_external_evidence_port_idx
on public.sc_external_evidence(lower(matched_port), published_at desc);

create index if not exists sc_external_evidence_chokepoint_idx
on public.sc_external_evidence(lower(matched_chokepoint), published_at desc);

create index if not exists sc_external_evidence_commodity_idx
on public.sc_external_evidence(lower(matched_commodity), published_at desc);

create index if not exists sc_external_evidence_country_idx
on public.sc_external_evidence(country_iso3, published_at desc);
