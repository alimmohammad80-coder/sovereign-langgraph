create table if not exists public.financial_risk_snapshots (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  captured_at timestamptz not null default now(),
  risk_score numeric,
  risk_level text,
  confidence_score numeric,
  methodology text,
  snapshot_json jsonb not null
);

create index if not exists financial_risk_snapshots_symbol_captured_idx
  on public.financial_risk_snapshots (symbol, captured_at desc);

create table if not exists public.financial_risk_reports (
  id uuid primary key default gen_random_uuid(),
  report_id text not null unique,
  symbol text not null,
  generated_at timestamptz not null default now(),
  risk_score numeric,
  methodology text,
  report_json jsonb not null
);

create index if not exists financial_risk_reports_symbol_generated_idx
  on public.financial_risk_reports (symbol, generated_at desc);

alter table public.financial_risk_snapshots enable row level security;
alter table public.financial_risk_reports enable row level security;

-- Supabase 2026 Data API defaults no longer guarantee new public tables are
-- reachable through PostgREST. Explicitly grant only the backend service role.
-- No anon/authenticated grants or policies are created: browser access remains
-- mediated through the Sovereign Intelligence FastAPI service.
grant select, insert on table public.financial_risk_snapshots to service_role;
grant select, insert on table public.financial_risk_reports to service_role;
revoke all on table public.financial_risk_snapshots from anon, authenticated;
revoke all on table public.financial_risk_reports from anon, authenticated;
