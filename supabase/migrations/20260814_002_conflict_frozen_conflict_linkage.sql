begin;

alter table conflict_frozen_conflicts
add column if not exists dispute_id text
references conflict_disputes(dispute_id)
on delete set null;

create index if not exists idx_conflict_frozen_dispute
on conflict_frozen_conflicts(dispute_id);

commit;
