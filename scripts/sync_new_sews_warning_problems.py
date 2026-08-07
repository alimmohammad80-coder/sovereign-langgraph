#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from app.routes.sews_evidence import get_sews_supabase_client
ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"app/data/sews_global_warning_registry.json"
RULES={"analyst_override_enabled":True,"confidence_model":"sews-confidence-v1","default_states":["DORMANT","WATCH","ADVISORY","WARNING","CRITICAL"],"hysteresis_enabled":True,"probability_model":"sews-logit-v1"}
def row(p):
    e={"description":p["description"],"countries":p["countries"],"region":p["region"],"subregions":p["geography"].get("subregions",[]),"maritime_zones":p["geography"].get("maritime_zones",[]),"map_geometry":p["geography"].get("map_geometry"),"classification":p["classification"],"dependencies":p["dependencies"],"ai_configuration":p["ai_configuration"],"governance":p["governance"],"outputs":p["outputs"]}
    return {"problem_key":p["problem_key"],"title":p["title"],"hypothesis":p["hypothesis"],"horizon_days":p["horizon_days"],"base_rate":p["base_rate"],"severity_score":p["severity_score"],"active":p["active"],"version":p["version"],"state":"DORMANT","transition_rules":RULES,"exposure_map":e}
ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); args=ap.parse_args()
db=get_sews_supabase_client(); items=json.loads(REG.read_text())["warning_problems"]
existing={x["problem_key"] for x in (db.table("sews_warning_problems").select("problem_key").range(0,9999).execute().data or [])}
missing=[x for x in items if x["problem_key"] not in existing]
print({"registry":len(items),"database":len(existing),"missing":len(missing)})
for x in missing: print("+",x["problem_key"],x["title"])
if not args.apply: print("DRY RUN ONLY. Re-run with --apply."); raise SystemExit
for x in missing: db.table("sews_warning_problems").insert(row(x)).execute()
print("Inserted:",len(missing))
