#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"app/data/sews_global_warning_registry.json"
d=json.loads(p.read_text()); items=d["warning_problems"]; keys=[x["problem_key"] for x in items]
errors=[]
if len(keys)!=len(set(keys)): errors.append("duplicate problem_key")
if d.get("warning_problem_count")!=len(items): errors.append("warning_problem_count mismatch")
for x in items:
    if x["classification"]["forecast_horizon_days"]!=x["horizon_days"]: errors.append(x["problem_key"]+": horizon mismatch")
    if x["geography"]["countries"]!=x["countries"]: errors.append(x["problem_key"]+": country mismatch")
print("count:",len(items)); print("domains:",dict(Counter(x["domain"] for x in items)))
if errors:
    print(*errors,sep="\n"); raise SystemExit(1)
print("VALIDATION PASSED")
