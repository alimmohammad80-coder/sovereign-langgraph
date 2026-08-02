create extension if not exists vector;

alter table public.sews_raw_evidence
add column if not exists embedding vector(1536);

alter table public.sews_raw_evidence
add column if not exists embedding_model text;

alter table public.sews_raw_evidence
add column if not exists embedded_at timestamptz;

create index if not exists sews_raw_evidence_embedding_idx
on public.sews_raw_evidence
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create or replace function public.match_sews_evidence(
    query_embedding vector(1536),
    match_threshold float,
    match_count integer
)
returns table (
    id uuid,
    title text,
    raw_text text,
    similarity float
)
language sql
stable
as $$
    select
        e.id,
        e.title,
        e.raw_text,
        1 - (e.embedding <=> query_embedding) as similarity
    from public.sews_raw_evidence e
    where e.embedding is not null
      and 1 - (e.embedding <=> query_embedding) >= match_threshold
    order by e.embedding <=> query_embedding
    limit match_count;
$$;
