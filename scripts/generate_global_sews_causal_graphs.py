from pprint import pprint

from app.routes.sews_evidence import (
    get_sews_supabase_client,
)
from app.services.sews_global_causal_graph_generator import (
    SEWSGlobalCausalGraphGenerator,
)

db = get_sews_supabase_client()

result = SEWSGlobalCausalGraphGenerator(
    db
).generate_all()

pprint(result)
