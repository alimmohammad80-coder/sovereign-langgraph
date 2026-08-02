# SEWS Operations Pipeline

Adds the orchestration layer:

Existing source bridge → raw evidence → deterministic indicator matching →
observation creation → indicator-state recalculation → deterministic assessment →
material-change detection → NVIDIA/Nemotron review → strategic product.

New routes:

POST /api/sews/operations/warning/run
POST /api/sews/operations/portfolio/run

Register:

from app.routes.sews_operations import router as sews_operations_router
app.include_router(sews_operations_router)

Start with a dry run for one warning. Do not run the portfolio persistently until
the single-warning pipeline completes successfully.

Important: inspect the exact signature of ObservationEvidenceLinkInput. If its
field names differ, adjust only the link-construction block.
