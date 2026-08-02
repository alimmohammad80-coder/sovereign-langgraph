from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_embedding_service import SEWSEmbeddingService

db = get_sews_supabase_client()
embedder = SEWSEmbeddingService()

query = "Closure of the Strait of Hormuz disrupting oil shipments"

vector = embedder.embed(
    query,
    input_type="query",
)

result = db.rpc(
    "match_sews_evidence",
    {
        "query_embedding": vector,
        "match_threshold": 0.50,
        "match_count": 5,
    },
).execute()

print("=" * 80)
print("Semantic Search Results")
print("=" * 80)

for i, row in enumerate(result.data, 1):
    print(f"{i}. Similarity: {row['similarity']:.3f}")
    print(row["title"])
    print("-" * 80)
