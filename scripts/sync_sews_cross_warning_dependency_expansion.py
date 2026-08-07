#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from app.routes.sews_evidence import get_sews_supabase_client

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "app/data/sews_cross_warning_dependency_additions_phase6_4.json"

def fetch_all(db, table, columns, page_size=500):
    out=[]; start=0
    while True:
        page=(db.table(table).select(columns).range(start,start+page_size-1).execute().data or [])
        out.extend(page)
        if len(page)<page_size: break
        start += page_size
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args=ap.parse_args()

    db=get_sews_supabase_client()
    catalog=json.loads(CATALOG.read_text())["relationships"]
    warning_keys={r["problem_key"] for r in fetch_all(db,"sews_warning_problems","problem_key")}
    bad=[r for r in catalog if r["source_problem_key"] not in warning_keys or r["target_problem_key"] not in warning_keys]
    if bad:
        print("Unknown warning keys found:")
        for r in bad: print(r)
        raise SystemExit(1)

    existing=fetch_all(
        db,
        "sews_warning_dependencies",
        "dependency_key,source_problem_key,target_problem_key,relationship_type"
    )
    identities={(r["source_problem_key"],r["target_problem_key"],r["relationship_type"]) for r in existing}
    missing=[r for r in catalog if (r["source_problem_key"],r["target_problem_key"],r["relationship_type"]) not in identities]

    print({
        "catalog_relationships": len(catalog),
        "existing_relationships": len(existing),
        "relationships_to_insert": len(missing),
        "final_expected": len(existing)+len(missing),
    })

    if not args.apply:
        print("DRY RUN ONLY. Re-run with --apply.")
        return

    inserted=0
    for row in missing:
        result=db.table("sews_warning_dependencies").insert(row).execute()
        if result.data:
            inserted += 1

    print("Inserted:", inserted)

if __name__=="__main__":
    main()
