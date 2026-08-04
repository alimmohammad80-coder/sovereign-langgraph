from pprint import pprint

from app.routes.sews_evidence import (
    get_sews_supabase_client,
)
from app.services.sews_cross_warning_dependency_generator import (
    SEWSCrossWarningDependencyGenerator,
)

db = get_sews_supabase_client()

result = SEWSCrossWarningDependencyGenerator(
    db
).generate_all()

pprint(result)
