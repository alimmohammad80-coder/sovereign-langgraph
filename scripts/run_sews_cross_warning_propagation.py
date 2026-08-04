from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_cross_warning_propagation_service import (
    SEWSCrossWarningPropagationService,
)

db = get_sews_supabase_client()

result = SEWSCrossWarningPropagationService(
    db
).propagate(
    persist=True,
)

pprint(result)
