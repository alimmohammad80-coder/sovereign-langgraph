# SEWS Ranked Matching Patch

This patch adds evidence-centric ranking and a cleanup script.

Important: the warning supervisor must call `rank_for_evidence(...)` and keep
only the top four indicators for each evidence record. Do not rerun the
persistent pipeline until that supervisor patch is applied.

Cleanup command:

PYTHONPATH=. python3 scripts/cleanup_sews_test_observations.py
