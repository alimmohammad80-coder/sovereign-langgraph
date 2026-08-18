alter table public.conflict_propagation_edges
add column if not exists relationship text
not null default 'related_to';

create index if not exists
idx_conflict_propagation_edges_relationship
on public.conflict_propagation_edges(
    relationship
)
where active = true;
