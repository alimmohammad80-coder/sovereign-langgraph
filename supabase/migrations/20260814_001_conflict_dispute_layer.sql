begin;

create table if not exists conflict_disputes (
  id uuid primary key default gen_random_uuid(),

  dispute_id text not null unique,
  name text not null,

  dispute_type text not null check (
    dispute_type in (
      'land_boundary',
      'territorial_sovereignty',
      'maritime_boundary',
      'eez',
      'island_sovereignty',
      'occupation',
      'separatist',
      'autonomy',
      'resource',
      'water',
      'demarcation',
      'ceasefire_line',
      'other'
    )
  ),

  status text not null check (
    status in (
      'latent',
      'active',
      'militarized',
      'negotiating',
      'ceasefire',
      'frozen',
      'resolved',
      'unknown'
    )
  ),

  parties jsonb not null default '[]'::jsonb,

  primary_dyad_id text
    references conflict_border_dyads(dyad_id)
    on delete set null,

  territory_id text
    references conflict_territories(territory_id)
    on delete set null,

  claimant_iso3 jsonb not null default '[]'::jsonb,

  maritime boolean not null default false,
  transboundary boolean not null default false,

  start_year integer check (
    start_year is null
    or start_year between 1800 and 2100
  ),

  last_major_incident date,

  current_mechanism text,
  legal_process text,

  geometry_ref text,

  source text not null,
  source_url text,
  source_version text,

  confidence_grade conflict_confidence_grade
    not null default 'unknown',

  review_status conflict_review_status
    not null default 'requires_review',

  last_reviewed date,

  active boolean not null default true,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists
idx_conflict_disputes_type
on conflict_disputes(dispute_type);

create index if not exists
idx_conflict_disputes_status
on conflict_disputes(status);

create index if not exists
idx_conflict_disputes_dyad
on conflict_disputes(primary_dyad_id);

create index if not exists
idx_conflict_disputes_active
on conflict_disputes(active);

create index if not exists
idx_conflict_disputes_maritime
on conflict_disputes(maritime);

alter table conflict_disputes
enable row level security;

commit;
