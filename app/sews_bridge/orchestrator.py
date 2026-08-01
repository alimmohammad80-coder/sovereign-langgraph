import json
from pathlib import Path
from supabase import Client
from app.sews_bridge.discovery import discover_sources
from app.sews_bridge.invocation import invoke_existing_source
from app.sews_bridge.normalization import normalize_existing_record
from app.sews_bridge.repository import SEWSBridgeRepository
from app.sews_bridge.schemas import BridgeRunResponse, BridgeSourceResult

REGISTRY_PATH = Path("app/data/sews_global_warning_registry.json")

class SEWSExistingSourcesBridge:
    def __init__(self, db: Client):
        self.db = db
        self.repository = SEWSBridgeRepository(db)

    @staticmethod
    def _problems(keys):
        problems = json.loads(REGISTRY_PATH.read_text())["warning_problems"]
        if not keys:
            return problems
        wanted = {k.upper() for k in keys}
        return [p for p in problems if p["problem_key"].upper() in wanted]

    @staticmethod
    def _queries(problem):
        queries = []
        for key in ("collection_queries", "search_queries", "queries"):
            value = problem.get(key)
            if isinstance(value, list):
                queries.extend(str(x) for x in value if x)
        if not queries:
            classification = problem.get("classification") or {}
            title = problem.get("title", "")
            hypothesis = problem.get("hypothesis", "")
            geography = classification.get("geographic_scope", "")
            queries = [title, f"{title} {geography}".strip(), hypothesis[:180]]
        seen, out = set(), []
        for q in queries:
            q = " ".join(str(q).split())
            if q and q.casefold() not in seen:
                seen.add(q.casefold())
                out.append(q)
        return out[:3]

    async def run(self, request):
        resolved, statuses = discover_sources()
        requested = {k.upper() for k in request.source_keys} if request.source_keys else set(resolved)
        problems = self._problems(request.problem_keys)
        results = []
        for source_key in sorted(requested):
            source = resolved.get(source_key)
            result = BridgeSourceResult(source_key=source_key, available=source is not None)
            if not source:
                status = next((s for s in statuses if s.source_key == source_key), None)
                result.errors.append(status.error if status and status.error else "Source not resolved")
                results.append(result)
                continue
            for problem in problems:
                c = problem.get("classification") or {}
                for query in self._queries(problem):
                    result.queries_attempted += 1
                    try:
                        raw = await invoke_existing_source(
                            source.callable, query=query, limit=request.limit_per_query,
                            country_iso3=c.get("country_iso3"), region=c.get("region_key")
                        )
                        records = [] if raw is None else (
                            raw if isinstance(raw, list) else (
                                raw.get("data") or raw.get("results") or raw.get("articles") or raw.get("records") or [raw]
                                if isinstance(raw, dict) else [raw]
                            )
                        )
                        result.records_received += len(records)
                        for item in records:
                            payload = normalize_existing_record(
                                source_key=source_key, raw_record=item,
                                problem_key=problem["problem_key"],
                                country_iso3=c.get("country_iso3"),
                                region_key=c.get("region_key"), query=query
                            )
                            result.records_normalized += 1
                            if request.persist and not request.dry_run:
                                inserted, _ = self.repository.persist_evidence(payload)
                                result.records_persisted += int(inserted)
                                result.duplicates_skipped += int(not inserted)
                    except Exception as exc:
                        result.errors.append(f"{problem['problem_key']} / {query}: {type(exc).__name__}: {exc}")
            results.append(result)
        return BridgeRunResponse(
            status="success",
            warning_problem_count=len(problems),
            source_results=results,
            total_records_received=sum(x.records_received for x in results),
            total_records_persisted=sum(x.records_persisted for x in results),
            metadata={"dry_run": request.dry_run, "persist": request.persist, "resolved_sources": sorted(resolved)},
        )
