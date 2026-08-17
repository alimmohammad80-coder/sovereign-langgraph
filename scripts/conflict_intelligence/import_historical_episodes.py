from app.services.conflict_intelligence.historical_episode_importer import (
    HistoricalEpisodeImporter,
)

SOURCE = "data/raw/ucdp_prio.csv"

importer = HistoricalEpisodeImporter(SOURCE)

importer.load()
importer.normalize()
importer.match_states()
importer.match_dyads()
importer.match_disputes()
importer.match_frozen_conflicts()
importer.validate()
importer.export_seed()
