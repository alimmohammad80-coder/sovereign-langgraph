from __future__ import annotations

from datetime import datetime, timezone

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_embedding_service import (
    MODEL,
    SEWSEmbeddingService,
)


def main() -> None:
    db = get_sews_supabase_client()
    service = SEWSEmbeddingService()

    rows = (
        db.table("sews_raw_evidence")
        .select("id,title,raw_text")
        .is_("embedding", "null")
        .order("collected_at")
        .limit(100)
        .execute()
        .data
        or []
    )

    print(f"Found {len(rows)} evidence records without embeddings.")

    completed = 0
    failed = 0

    for row in rows:
        text = "\n\n".join(
            value.strip()
            for value in (
                row.get("title"),
                row.get("raw_text"),
            )
            if isinstance(value, str) and value.strip()
        )

        if not text:
            failed += 1
            print(f"Skipped {row['id']}: no usable text.")
            continue

        try:
            vector = service.embed(
                text,
                input_type="passage",
            )

            (
                db.table("sews_raw_evidence")
                .update(
                    {
                        "embedding": vector,
                        "embedding_model": MODEL,
                        "embedded_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    }
                )
                .eq("id", row["id"])
                .execute()
            )

            completed += 1
            print(f"Embedded {row['id']}")

        except Exception as exc:
            failed += 1
            print(
                f"Failed {row['id']}: "
                f"{type(exc).__name__}: {exc}"
            )

    print(
        f"Completed: {completed} | Failed: {failed}"
    )


if __name__ == "__main__":
    main()
