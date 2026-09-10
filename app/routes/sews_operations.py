from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from supabase import Client

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_operations import (
    WarningSupervisorRunRequest,
    PortfolioSupervisorRunRequest,
    EvidencePipelineResponse,
    PortfolioSupervisorRunResponse,
)
from app.services.sews_warning_supervisor import SEWSWarningSupervisor
from app.services.sews_portfolio_supervisor import SEWSPortfolioSupervisor
from app.services.sews_portfolio_refresh_service import SEWSPortfolioRefreshService


router = APIRouter(prefix="/api/sews/operations", tags=["SEWS Operations"])
_scheduler_task: asyncio.Task | None = None


def get_db() -> Client:
    return get_sews_supabase_client()


@router.post("/warning/run", response_model=EvidencePipelineResponse)
async def run_warning(payload: WarningSupervisorRunRequest, db: Client = Depends(get_db)):
    return await SEWSWarningSupervisor(db).run(payload)


@router.post("/portfolio/run", response_model=PortfolioSupervisorRunResponse)
async def run_portfolio(payload: PortfolioSupervisorRunRequest, db: Client = Depends(get_db)):
    return await SEWSPortfolioSupervisor(db).run(payload)


@router.post("/portfolio/refresh-v2")
async def refresh_portfolio_v2(
    payload: PortfolioSupervisorRunRequest,
    db: Client = Depends(get_db),
):
    """Run collection -> deterministic scoring -> evidence-grounded OA/2.0 production."""
    return await SEWSPortfolioRefreshService(db).refresh(
        problem_keys=payload.problem_keys,
        concurrency=payload.concurrency,
        limit_per_query=payload.limit_per_query,
    )


def _scheduled_batch(keys: list[str], batch_size: int) -> list[str]:
    if not keys:
        return []
    # Deterministic rotation based on UTC hour. This survives app restarts and
    # covers the whole registry without local checkpoint state.
    now = datetime.now(timezone.utc)
    hour_index = (now.toordinal() * 24) + now.hour
    start = (hour_index * batch_size) % len(keys)
    return [keys[(start + i) % len(keys)] for i in range(min(batch_size, len(keys)))]


async def _embedded_scheduler_loop() -> None:
    # Give the web process time to become healthy before external collection.
    await asyncio.sleep(int(os.getenv("SEWS_SCHEDULER_START_DELAY_SECONDS", "90")))

    interval = max(900, int(os.getenv("SEWS_SCHEDULER_INTERVAL_SECONDS", "3600")))
    batch_size = max(1, min(12, int(os.getenv("SEWS_SCHEDULER_BATCH_SIZE", "6"))))
    concurrency = max(1, min(4, int(os.getenv("SEWS_SCHEDULER_CONCURRENCY", "2"))))
    limit_per_query = max(1, min(20, int(os.getenv("SEWS_SCHEDULER_LIMIT_PER_QUERY", "5"))))

    while True:
        try:
            db = get_sews_supabase_client()
            service = SEWSPortfolioRefreshService(db)
            keys = service.active_problem_keys()
            batch = _scheduled_batch(keys, batch_size)
            if batch:
                result = await service.refresh(
                    problem_keys=batch,
                    concurrency=concurrency,
                    limit_per_query=limit_per_query,
                )
                print(
                    "SEWS portfolio refresh: "
                    f"status={result.get('status')} "
                    f"problems={len(batch)} "
                    f"products={result.get('products_generated')} "
                    f"blocked_no_evidence={result.get('products_blocked_no_evidence')}"
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"SEWS embedded scheduler error: {type(exc).__name__}: {exc}")

        await asyncio.sleep(interval)


@router.on_event("startup")
async def start_sews_embedded_scheduler() -> None:
    global _scheduler_task
    enabled = os.getenv("SEWS_EMBEDDED_SCHEDULER_ENABLED", "true").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_embedded_scheduler_loop())


@router.on_event("shutdown")
async def stop_sews_embedded_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is None:
        return
    _scheduler_task.cancel()
    with suppress(asyncio.CancelledError):
        await _scheduler_task
    _scheduler_task = None
