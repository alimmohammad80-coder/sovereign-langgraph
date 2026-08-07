from __future__ import annotations

from collections import Counter, defaultdict

from app.routes.sews_evidence import get_sews_supabase_client


CURATED_VALIDATION_VERSION = "sews-curated-analytic-validation-v1"
SUPPORTED_DIRECTIONAL_TYPES = {
    "AMPLIFIES",
    "CAUSES",
    "TRANSMITS",
    "MITIGATES",
    "INHIBITS",
}


def fetch_all(db, table: str, columns: str, page_size: int = 500):
    rows = []
    start = 0
    while True:
        page = (
            db.table(table)
            .select(columns)
            .range(start, start + page_size - 1)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows


def main() -> None:
    db = get_sews_supabase_client()
    warnings = fetch_all(
        db,
        "sews_warning_problems",
        "problem_key,title,active",
    )
    dependencies = fetch_all(
        db,
        "sews_warning_dependencies",
        "*",
    )

    warning_keys = {
        row["problem_key"]
        for row in warnings
        if row.get("active") is True
    }

    errors = []
    seen = set()
    incoming = defaultdict(int)
    outgoing = defaultdict(int)

    for row in dependencies:
        if row.get("active") is not True:
            continue

        source = row.get("source_problem_key")
        target = row.get("target_problem_key")
        relationship_type = str(
            row.get("relationship_type") or ""
        ).upper()
        direction_status = str(
            row.get("direction_status") or ""
        ).upper()
        metadata = row.get("metadata") or {}
        identity = (source, target, relationship_type)

        if source not in warning_keys:
            errors.append(f"Unknown source warning: {source}")
        if target not in warning_keys:
            errors.append(f"Unknown target warning: {target}")
        if source == target:
            errors.append(f"Self-link: {identity}")
        if identity in seen:
            errors.append(f"Duplicate relationship: {identity}")
        seen.add(identity)

        if source:
            outgoing[source] += 1
        if target:
            incoming[target] += 1

        if (
            metadata.get("validation_version")
            == CURATED_VALIDATION_VERSION
        ):
            if direction_status != "VALIDATED":
                errors.append(
                    f"Curated relationship is not VALIDATED: {identity}"
                )
            if relationship_type not in SUPPORTED_DIRECTIONAL_TYPES:
                errors.append(
                    f"Curated relationship lost directional type: {identity}"
                )

    isolated = sorted(
        key
        for key in warning_keys
        if incoming[key] == 0 and outgoing[key] == 0
    )

    print(
        {
            "active_warnings": len(warning_keys),
            "dependencies": len(dependencies),
            "isolated_warnings": len(isolated),
            "relationship_types": dict(
                Counter(
                    str(row.get("relationship_type") or "").upper()
                    for row in dependencies
                    if row.get("active") is True
                )
            ),
            "direction_statuses": dict(
                Counter(
                    str(row.get("direction_status") or "").upper()
                    for row in dependencies
                    if row.get("active") is True
                )
            ),
            "errors": len(errors),
        }
    )

    for key in isolated:
        print("ISOLATED:", key)
    for error in errors:
        print("ERROR:", error)

    if isolated or errors:
        raise SystemExit(1)

    print("VALIDATION PASSED — read-only; no dependency contracts were modified.")


if __name__ == "__main__":
    main()
