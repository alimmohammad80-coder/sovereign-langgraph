-- Quarantine empty, unreferenced legacy tables.
-- This migration is idempotent because production was quarantined
-- manually after the August 13, 2026 dependency audit.
-- No table or data is permanently deleted.

create schema if not exists quarantine_20260813;

do $$
declare
    candidate text;
    row_total bigint;
    candidates text[] := array[
        'agent_handoff_queue',
        'commodity_financial_shocks',
        'country_report_cache',
        'forecast_runs',
        'fx_risk_indicators',
        'global_risk_score_history',
        'intelligence_signals',
        'news_articles',
        'published_briefings',
        'sanctions_financial_exposure',
        'sc_port_commodity_exposure',
        'sews_signals',
        'source_health_logs',
        'sovereign_debt_indicators',
        'user_alert_watchlists',
        'user_financial_watchlists',
        'weekly_briefs'
    ];
begin
    foreach candidate in array candidates
    loop
        if to_regclass(
            format('public.%I', candidate)
        ) is not null then
            execute format(
                'select count(*) from public.%I',
                candidate
            )
            into row_total;

            if row_total <> 0 then
                raise exception
                    'Quarantine stopped: public.% contains % rows',
                    candidate,
                    row_total;
            end if;

            execute format(
                'alter table public.%I '
                'set schema quarantine_20260813',
                candidate
            );

        elsif to_regclass(
            format(
                'quarantine_20260813.%I',
                candidate
            )
        ) is null then
            raise exception
                'Table % exists in neither public nor quarantine',
                candidate;
        end if;
    end loop;
end
$$;
