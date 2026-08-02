import asyncio
from supabase import Client
from app.schemas.sews_operations import PortfolioSupervisorRunRequest, PortfolioSupervisorRunResponse, WarningSupervisorRunRequest, EvidencePipelineResponse
from app.services.sews_warning_supervisor import SEWSWarningSupervisor

class SEWSPortfolioSupervisor:
    def __init__(self, db: Client):
        self.db = db

    def _problem_keys(self):
        result = self.db.table("sews_warning_problems").select("problem_key").eq("active", True).order("problem_key").range(0, 4999).execute()
        return [row["problem_key"] for row in (result.data or [])]

    async def run(self, request: PortfolioSupervisorRunRequest):
        keys = request.problem_keys or self._problem_keys()
        semaphore = asyncio.Semaphore(request.concurrency)

        async def run_one(key):
            async with semaphore:
                return await SEWSWarningSupervisor(self.db).run(
                    WarningSupervisorRunRequest(
                        problem_key=key,
                        dry_run=request.dry_run,
                        limit_per_query=request.limit_per_query,
                    )
                )

        raw = await asyncio.gather(*(run_one(k) for k in keys), return_exceptions=True)
        results = []
        failed = 0

        for key, item in zip(keys, raw):
            if isinstance(item, Exception):
                failed += 1
                results.append(EvidencePipelineResponse(status="failed", problem_key=key, errors=[f"{type(item).__name__}: {item}"]))
            else:
                results.append(item)
                failed += int(item.status == "failed")

        return PortfolioSupervisorRunResponse(
            status="success" if failed == 0 else "partial",
            total_warning_problems=len(keys),
            completed=len(keys) - failed,
            failed=failed,
            material_changes=sum(1 for item in results if item.material_change),
            results=results,
        )
