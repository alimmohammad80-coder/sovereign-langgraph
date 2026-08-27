-- ============================================================
-- Conflict Intelligence Evidence Foundation
-- Additive migration: preserves any existing table/data.
-- ============================================================

create table if not exists public.conflict_evidence (
    id uuid primary key default gen_random_uuid()
);

alter table public.conflict_evidence
    add column if not exists evidence_key text,
    add column if not exists conflict_id integer,
    add column if not exists canonical_episode_id uuid,

    add column if not exists evidence_type text default 'news_event',
    add column if not exists event_type text,

    add column if not exists title text,
    add column if not exists summary text,

    add column if not exists observed_at timestamptz,
    add column if not exists published_at timestamptz,

    add column if not exists countries text[] not null default '{}',
    add column if not exists territories text[] not null default '{}',
    add column if not exists actors text[] not null default '{}',

    add column if not exists severity numeric,
    add column if not exists confidence numeric,

    add column if not exists supports_escalation boolean,
    add column if not exists contradicts_escalation boolean not null default false,

    add column if not exists source_name text,
    add column if not exists source_url text,
    add column if not exists source_type text,
    add column if not exists source_reliability numeric,

    add column if not exists citation_text text,

    add column if not exists raw_payload jsonb not null default '{}'::jsonb,

    add column if not exists review_status text not null default 'unreviewed',
    add column if not exists active boolean not null default true,

    add column if not exists created_at timestamptz not null default now(),
    add column if not exists updated_at timestamptz not null default now();

alter table public.conflict_evidence
    alter column evidence_key set not null;

alter table public.conflict_evidence
    drop constraint if exists conflict_evidence_evidence_key_key;

alter table public.conflict_evidence
    add constraint conflict_evidence_evidence_key_key
    unique (evidence_key);

create index if not exists
    conflict_evidence_conflict_idx
    on public.conflict_evidence(conflict_id);

create index if not exists
    conflict_evidence_episode_idx
    on public.conflict_evidence(canonical_episode_id);

create index if not exists
    conflict_evidence_observed_idx
    on public.conflict_evidence(observed_at desc);

create index if not exists
    conflict_evidence_published_idx
    on public.conflict_evidence(published_at desc);

create index if not exists
    conflict_evidence_event_type_idx
    on public.conflict_evidence(event_type);

create index if not exists
    conflict_evidence_source_idx
    on public.conflict_evidence(source_name);

create index if not exists
    conflict_evidence_active_idx
    on public.conflict_evidence(active);
