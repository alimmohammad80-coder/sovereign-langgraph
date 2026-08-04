from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_cross_warning_dependency_validator import (
    SEWSCrossWarningDependencyValidator,
)

db = get_sews_supabase_client()

pprint(
    SEWSCrossWarningDependencyValidator(
        db
    ).validate_all()
)
