alter table public.conflict_analysis_jobs
    alter column conflict_id drop not null;

alter table public.conflict_analysis_jobs
    add column if not exists request_mode text
    not null default 'canonical';

alter table public.conflict_analysis_jobs
    add column if not exists request_json jsonb;

alter table public.conflict_analysis_jobs
    add constraint conflict_analysis_jobs_request_mode_check
    check (
        request_mode in (
            'canonical',
            'agent_selection'
        )
    );
