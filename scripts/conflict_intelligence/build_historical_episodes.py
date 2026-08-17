from app.services.conflict_intelligence.historical_episode_builder import (
    HistoricalEpisodeBuilder,
)

builder = HistoricalEpisodeBuilder(
    "data/raw/ucdp_prio.csv"
)

builder.build()
