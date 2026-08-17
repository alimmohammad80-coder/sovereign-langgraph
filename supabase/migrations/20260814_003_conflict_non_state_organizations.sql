begin;

create table if not exists conflict_non_state_organizations (
  id uuid primary key default gen_random_uuid(),

  organization_id text not null unique,
  name text not null,
  aliases jsonb not null default '[]'::jsonb,

  active boolean not null default true,

  areas_of_operation_iso3 jsonb not null default '[]'::jsonb,
  territory_refs jsonb not null default '[]'::jsonb,

  estimated_strength integer check (
    estimated_strength is null
    or estimated_strength >= 0
  ),

  headquarters_location text,

  external_ids jsonb not null default '{}'::jsonb,

  source text not null,
  source_url text,
  source_version text,

  confidence_grade conflict_confidence_grade
    not null default 'unknown',

  review_status conflict_review_status
    not null default 'requires_review',

  last_reviewed date,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);


create table if not exists conflict_governing_authorities (
  id uuid primary key default gen_random_uuid(),

  relationship_id text not null unique,

  organization_id text not null
    references conflict_non_state_organizations(organization_id)
    on delete cascade,

  state_iso3 text
    references conflict_countries(iso3)
    on delete set null,

  territory_id text
    references conflict_territories(territory_id)
    on delete set null,

  control_scope text not null check (
    control_scope in (
      'local',
      'regional',
      'subnational',
      'national',
      'territorial',
      'unknown'
    )
  ),

  effective_control boolean not null default false,

  control_start_date date,
  control_end_date date,

  recognition_status text not null check (
    recognition_status in (
      'un_recognized_government',
      'partially_recognized',
      'contested',
      'not_un_recognized_government',
      'not_applicable',
      'unknown'
    )
  ),

  recognition_source text,
  recognition_source_url text,

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
  updated_at timestamptz not null default now(),

  check (
    state_iso3 is not null
    or territory_id is not null
  )
);


create index if not exists
idx_conflict_nso_active
on conflict_non_state_organizations(active);

create index if not exists
idx_conflict_nso_review
on conflict_non_state_organizations(review_status);

create index if not exists
idx_conflict_governing_org
on conflict_governing_authorities(organization_id);

create index if not exists
idx_conflict_governing_state
on conflict_governing_authorities(state_iso3);

create index if not exists
idx_conflict_governing_territory
on conflict_governing_authorities(territory_id);

create index if not exists
idx_conflict_governing_control
on conflict_governing_authorities(
  effective_control,
  control_scope
);

alter table conflict_non_state_organizations
enable row level security;

alter table conflict_governing_authorities
enable row level security;

commit;
