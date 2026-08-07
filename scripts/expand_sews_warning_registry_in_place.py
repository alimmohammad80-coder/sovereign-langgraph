#!/usr/bin/env python3
import argparse, json, shutil
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"app/data/sews_global_warning_registry.json"
ADD=ROOT/"app/data/sews_warning_registry_additions_phase6_1.json"
ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); args=ap.parse_args()
registry=json.loads(REG.read_text()); additions=json.loads(ADD.read_text())["warning_problems"]
existing=registry["warning_problems"]; keys={x["problem_key"] for x in existing}
new=[x for x in additions if x["problem_key"] not in keys]
print({"existing":len(existing),"packaged":len(additions),"new":len(new),"final":len(existing)+len(new)})
if not args.apply:
    print("DRY RUN ONLY. Re-run with --apply."); raise SystemExit
backup=REG.with_suffix(f".json.bak_phase6_1_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
shutil.copy2(REG,backup)
registry["warning_problems"].extend(new)
registry["warning_problem_count"]=len(registry["warning_problems"])
registry["registry_version"]="sews-global-registry-v1.1"
REG.write_text(json.dumps(registry,indent=2,ensure_ascii=False)+"\n")
print("Updated:",REG); print("Backup:",backup)
