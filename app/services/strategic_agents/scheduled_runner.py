from __future__ import annotations

import asyncio
import json
import os
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from app.services.strategic_agents.agent_orchestrator import (
    strategic_agent_orchestrator,
)
from app.services.strategic_agents.agent_registry import (
    AGENT_REGISTRY,
)


DOMAIN_AGENTS = (
    "conflict_monitoring",
    "political_stability",
    "economic_risk",
    "energy_security",
    "trade_sanctions",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def scheduler_enabled() -> bool:
    return os.getenv(
        "STRATEGIC_AGENT_SCHEDULER_ENABLED",
        "false",
    ).lower() in {"1", "true", "yes", "on"}


def load_scopes() -> list[dict[str, str]]:
    raw_json = os.getenv("STRATEGIC_AGENT_SCOPES_JSON", "").strip()

    if raw_json:
        try:
            parsed = json.loads(raw_json)

            if isinstance(parsed, list):
                return [
                    {
                        "country_iso3": str(item["country_iso3"]),
                        "country_name": str(item["country_name"]),
                        "region": str(item.get("region") or ""),
                    }
                    for item in parsed
                    if isinstance(item, dict)
                    and item.get("country_iso3")
                    and item.get("country_name")
                ]
        except Exception as exc:
            print(
                "[StrategicAgentScheduler] Invalid "
                f"STRATEGIC_AGENT_SCOPES_JSON: {exc}"
            )

    countries = [
        value.strip().upper()
        for value in os.getenv(
            "STRATEGIC_AGENT_DEFAULT_COUNTRIES",
            "IRN",
        ).split(",")
        if value.strip()
    ]

    known_scopes = {
        "IRN": {
            "country_iso3": "IRN",
            "country_name": "Iran",
            "region": "Middle East",
        },
    }

    return [
        known_scopes[iso3]
        for iso3 in countries
        if iso3 in known_scopes
    ]


class StrategicAgentScheduledRunner:
    def __init__(self) -> None:
        self._task: asyncio.Task[Any] | None = None
        self._stop_event = asyncio.Event()
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_run_monotonic: dict[str, float] = {}
        self._state: dict[str, Any] = {
            "enabled": False,
            "running": False,
            "started_at": None,
            "last_cycle_at": None,
            "last_error": None,
            "active_jobs": [],
        }

    def status(self) -> dict[str, Any]:
        return {
            **self._state,
            "scopes": load_scopes(),
        }

    async def start(self) -> None:
        if not scheduler_enabled():
            self._state["enabled"] = False
            print("[StrategicAgentScheduler] Disabled.")
            return

        if self._task and not self._task.done():
            return

        self._state.update(
            {
                "enabled": True,
                "running": True,
                "started_at": utc_now_iso(),
                "last_error": None,
            }
        )

        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._scheduler_loop(),
            name="strategic-agent-scheduler",
        )

        print("[StrategicAgentScheduler] Started.")

    async def stop(self) -> None:
        self._stop_event.set()

        if self._task:
            self._task.cancel()

            with suppress(asyncio.CancelledError):
                await self._task

        self._task = None
        self._state["running"] = False

        print("[StrategicAgentScheduler] Stopped.")

    async def _scheduler_loop(self) -> None:
        # Allow the API to finish starting before background collection.
        await asyncio.sleep(20)

        while not self._stop_event.is_set():
            try:
                await self._run_due_agents()
                self._state["last_cycle_at"] = utc_now_iso()
                self._state["last_error"] = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._state["last_error"] = str(exc)
                print(
                    "[StrategicAgentScheduler] Cycle error:",
                    str(exc),
                )

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                pass

    async def _run_due_agents(self) -> None:
        loop = asyncio.get_running_loop()
        now = loop.time()
        scopes = load_scopes()

        if not scopes:
            print(
                "[StrategicAgentScheduler] "
                "No configured country scopes."
            )
            return

        for scope in scopes:
            changed_domains: list[str] = []

            for agent_key in DOMAIN_AGENTS:
                definition = AGENT_REGISTRY[agent_key]
                interval_seconds = (
                    definition.default_schedule_minutes * 60
                )

                job_key = (
                    f"{agent_key}:"
                    f"{scope['country_iso3']}"
                )

                last_run = self._last_run_monotonic.get(job_key)

                if (
                    last_run is not None
                    and now - last_run < interval_seconds
                ):
                    continue

                result = await self._run_one(
                    agent_key=agent_key,
                    scope=scope,
                )

                self._last_run_monotonic[job_key] = loop.time()

                if result.get("status") == "success":
                    changed_domains.append(agent_key)

            # Executive Briefing runs after one or more domain agents
            # successfully refresh in this scheduler cycle.
            if changed_domains:
                await self._run_one(
                    agent_key="executive_briefing",
                    scope=scope,
                )

    async def _run_one(
        self,
        agent_key: str,
        scope: dict[str, str],
    ) -> dict[str, Any]:
        job_key = f"{agent_key}:{scope['country_iso3']}"
        lock = self._locks.setdefault(job_key, asyncio.Lock())

        if lock.locked():
            print(
                "[StrategicAgentScheduler] Skipping overlapping job:",
                job_key,
            )
            return {
                "status": "skipped",
                "reason": "already_running",
            }

        async with lock:
            self._state["active_jobs"] = [
                *self._state["active_jobs"],
                job_key,
            ]

            try:
                print(
                    "[StrategicAgentScheduler] Running:",
                    job_key,
                )

                context = {
                    "country_iso3": scope["country_iso3"],
                    "country_name": scope["country_name"],
                    "region": scope.get("region"),
                    "signals": [],
                    "signal_limit": 20,
                    "timeframe": "180 days",
                }

                result = (
                    await strategic_agent_orchestrator.run_agent(
                        agent_key=agent_key,
                        context=context,
                        trigger_type="scheduled",
                    )
                )

                print(
                    "[StrategicAgentScheduler] Completed:",
                    job_key,
                    result.get("status"),
                )

                return result

            finally:
                self._state["active_jobs"] = [
                    item
                    for item in self._state["active_jobs"]
                    if item != job_key
                ]


strategic_agent_scheduled_runner = (
    StrategicAgentScheduledRunner()
)
