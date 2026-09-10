import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from supabase import Client
from app.sews_bridge.discovery import discover_sources
from app.sews_bridge.invocation import invoke_existing_source
from app.sews_bridge.normalization import normalize_existing_record
from app.sews_bridge.repository import SEWSBridgeRepository
from app.sews_bridge.schemas import BridgeRunResponse, BridgeSourceResult

REGISTRY_PATH = Path("app/data/sews_global_warning_registry.json")
NEWS_EVENT_SOURCES = {"GOOGLE_NEWS_RSS", "GDELT", "NEWSAPI"}
DEFAULT_NEWS_LOOKBACK_DAYS = 14


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

    @staticmethod
    def _source_keys_for_problem(problem):
        """Select intelligence families according to the warning problem."""
        key = str(problem.get("problem_key") or "").upper()
        title = str(problem.get("title") or "").lower()
        hypothesis = str(problem.get("hypothesis") or "").lower()
        classification = problem.get("classification") or {}

        blob = " ".join([
            key.lower(),
            title,
            hypothesis,
            str(classification).lower(),
        ])

        sources = {"GOOGLE_NEWS_RSS", "GDELT", "NEWSAPI"}

        economic_terms = (
            "currency", "debt", "bank", "financial", "recession", "inflation",
            "economic", "price", "trade", "sovereign",
        )
        energy_terms = (
            "energy", "gas", "oil", "lng", "pipeline", "hormuz", "shipping",
            "suez", "canal", "port", "semiconductor", "supply",
        )
        conflict_terms = (
            "conflict", "war", "military", "escalation", "border", "blockade",
            "militancy", "spillover", "coup", "regime", "state collapse",
        )
        political_terms = (
            "political", "election", "protest", "disinformation", "interference",
            "instability", "governance",
        )
        trade_terms = (
            "sanction", "trade", "tariff", "export", "mineral", "shipping",
            "supply chain",
        )

        if any(term in blob for term in economic_terms):
            sources.add("SEWS_ECONOMIC")
        if any(term in blob for term in energy_terms):
            sources.add("SEWS_ENERGY")
        if any(term in blob for term in conflict_terms):
            sources.add("SEWS_CONFLICT")
        if any(term in blob for term in political_terms):
            sources.add("SEWS_POLITICAL")
        if any(term in blob for term in trade_terms):
            sources.add("SEWS_TRADE_SANCTIONS")

        return sources

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None

        if isinstance(value, datetime):
            dt = value
        else:
            raw = str(value).strip()
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                try:
                    dt = parsedate_to_datetime(raw)
                except Exception:
                    return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @classmethod
    def _fresh_enough(cls, source_key, payload, requested_cutoff):
        published = cls._parse_datetime(
            payload.get("published_at") or payload.get("observed_at")
        )

        cutoff = cls._parse_datetime(requested_cutoff) if requested_cutoff else None
        if cutoff is not None:
            return published is not None and published > cutoff

        # Fast-moving event/news feeds must never treat undated or arbitrarily
        # old material as current warning evidence. Slower structured sources
        # retain their natural update cadence unless the caller sets a cutoff.
        if source_key in NEWS_EVENT_SOURCES:
            if published is None:
                return False
            default_cutoff = datetime.now(timezone.utc) - timedelta(
                days=DEFAULT_NEWS_LOOKBACK_DAYS
            )
            return published > default_cutoff

        return True

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
                allowed_sources = self._source_keys_for_problem(problem)
                if source_key not in allowed_sources:
                    continue

                c = problem.get("classification") or {}
                for query in self._queries(problem):
                    result.queries_attempted += 1
                    try:
                        raw = await invoke_existing_source(
                            source.callable,
                            query=query,
                            limit=request.limit_per_query,
                            country_iso3=c.get("country_iso3"),
                            region=c.get("region_key"),
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
                                source_key=source_key,
                                raw_record=item,
                                problem_key=problem["problem_key"],
                                country_iso3=c.get("country_iso3"),
                                region_key=c.get("region_key"),
                                query=query,
                            )
                            result.records_normalized += 1

                            if not self._fresh_enough(
                                source_key,
                                payload,
                                request.collect_since,
                            ):
                                continue

                            result.records_after_freshness_filter += 1

                            if request.persist and not request.dry_run:
                                inserted, _ = self.repository.persist_evidence(payload)
                                result.records_persisted += int(inserted)
                                result.duplicates_skipped += int(not inserted)
                    except Exception as exc:
                        result.errors.append(
                            f"{problem['problem_key']} / {query}: {type(exc).__name__}: {exc}"
                        )
            results.append(result)
        return BridgeRunResponse(
            status="success",
            warning_problem_count=len(problems),
            source_results=results,
            total_records_received=sum(x.records_received for x in results),
            total_records_persisted=sum(x.records_persisted for x in results),
            metadata={
                "dry_run": request.dry_run,
                "persist": request.persist,
                "collect_since": request.collect_since,
                "default_news_lookback_days": DEFAULT_NEWS_LOOKBACK_DAYS,
                "resolved_sources": sorted(resolved),
            },
        )
