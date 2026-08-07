#!/usr/bin/env python3
from __future__ import annotations
from collections import defaultdict
from app.routes.sews_evidence import get_sews_supabase_client

def fetch_all(db, table, columns, page_size=500):
    out=[]; start=0
    while True:
        page=(db.table(table).select(columns).range(start,start+page_size-1).execute().data or [])
        out.extend(page)
        if len(page)<page_size: break
        start += page_size
    return out

db=get_sews_supabase_client()
warnings=fetch_all(db,"sews_warning_problems","problem_key,title")
rels=fetch_all(db,"sews_warning_dependencies","*")
keys={w["problem_key"] for w in warnings}
incoming=defaultdict(int); outgoing=defaultdict(int); errors=[]; seen=set()

for r in rels:
    src=r.get("source_problem_key"); tgt=r.get("target_problem_key"); typ=r.get("relationship_type")
    ident=(src,tgt,typ)
    if src not in keys or tgt not in keys: errors.append(f"unknown key: {ident}")
    if src==tgt: errors.append(f"self-link: {ident}")
    if ident in seen: errors.append(f"duplicate: {ident}")
    seen.add(ident)
    if src: outgoing[src]+=1
    if tgt: incoming[tgt]+=1

isolated=sorted(k for k in keys if incoming[k]==0 and outgoing[k]==0)
print({
    "warnings":len(keys),
    "relationships":len(rels),
    "warnings_connected":len(keys)-len(isolated),
    "warnings_isolated":len(isolated),
    "errors":len(errors),
})
if isolated:
    print("Isolated warnings:")
    for k in isolated: print(" -",k)
if errors:
    print("Errors:")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

if isolated:
    raise SystemExit(
        f"VALIDATION FAILED: {len(isolated)} warnings remain isolated."
    )

print("VALIDATION PASSED")
