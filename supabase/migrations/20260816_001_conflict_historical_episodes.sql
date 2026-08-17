-- ============================================================================
-- CONFLICT HISTORICAL EPISODES
-- Sovereign Intelligence AI
-- ============================================================================

DROP TABLE IF EXISTS public.conflict_historical_episodes CASCADE;

CREATE TABLE public.conflict_historical_episodes (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    conflict_id INTEGER NOT NULL,
    year INTEGER NOT NULL,

    location TEXT,
    region TEXT,

    side_a_iso3 TEXT,
    side_b_iso3 TEXT,

    intensity_level INTEGER,
    conflict_type INTEGER,

    territory_name TEXT,

    start_date DATE,

    episode_end BOOLEAN,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT conflict_historical_episode_unique
        UNIQUE (conflict_id, year)
);

CREATE INDEX idx_conflict_hist_conflict
ON public.conflict_historical_episodes(conflict_id);

CREATE INDEX idx_conflict_hist_year
ON public.conflict_historical_episodes(year);

CREATE INDEX idx_conflict_hist_side_a
ON public.conflict_historical_episodes(side_a_iso3);

CREATE INDEX idx_conflict_hist_side_b
ON public.conflict_historical_episodes(side_b_iso3);

CREATE INDEX idx_conflict_hist_region
ON public.conflict_historical_episodes(region);

CREATE INDEX idx_conflict_hist_location
ON public.conflict_historical_episodes(location);

COMMENT ON TABLE public.conflict_historical_episodes IS
'Historical armed conflict episodes imported from UCDP/PRIO and linked into the Sovereign Intelligence Conflict Graph.';
