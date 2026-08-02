from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_evidence_deduplication_service import (
    SEWSEvidenceDeduplicationService,
)


db = get_sews_supabase_client()

result = SEWSEvidenceDeduplicationService(db).run(
    "WP-HORMUZ-CLOSURE"
)

pprint(result)
