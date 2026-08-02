drop index if exists public.sews_raw_evidence_embedding_idx;

drop function if exists public.match_sews_evidence(
    vector,
    double precision,
    integer
);

alter table public.sews_raw_evidence
alter column embedding type vector(2048)
using null::vector(2048);

create index if not exists sews_raw_evidence_embedding_idx
on public.sews_raw_evidence
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create or replace function public.match_sews_evidence(
    query_embedding vector(2048),
    match_threshold double precision default 0.65,
    match_count integer default 20
)
returns table (
    id uuid,
    title text,
    raw_text text,
    similarity double precision
)
language sql
stable
as $$
    select
        evidence.id,
        evidence.title,
        evidence.raw_text,
        (
            1 - (
                evidence.embedding
                <=> query_embedding
            )
        )::double precision as similarity
    from public.sews_raw_evidence evidence
    where evidence.embedding is not null
      and (
          1 - (
              evidence.embedding
              <=> query_embedding
          )
      ) >= match_threshold
    order by evidence.embedding <=> query_embedding
    limit match_count;
$$;
