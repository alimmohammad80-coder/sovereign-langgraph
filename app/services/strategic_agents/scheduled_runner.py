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
from app.services.strategic_agents.material_change import (
    detect_material_change,
    load_latest_assessment,
)
from app.services.strategic_agents.regional_scopes import (
    build_region_scope,
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


def load_scopes() -> list[dict[str, Any]]:
    raw_json = os.getenv(
        "STRATEGIC_AGENT_REGIONS_JSON",
        "",
    ).strip()

    requested_regions: list[str] = []

    if raw_json:
        try:
            parsed = json.loads(raw_json)

            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, str):
                        requested_regions.append(item)
                    elif (
                        isinstance(item, dict)
                        and item.get("region")
                    ):
                        requested_regions.append(
                            str(item["region"])
                        )
        except Exception as exc:
            print(
                "[StrategicAgentScheduler] Invalid "
                f"STRATEGIC_AGENT_REGIONS_JSON: {exc}"
            )

    if not requested_regions:
        requested_regions = [
            value.strip()
            for value in os.getenv(
                "STRATEGIC_AGENT_DEFAULT_REGIONS",
                "Middle East",
            ).split(",")
            if value.strip()
        ]

    scopes = []

    for region in requested_regions:
        try:
            scopes.append(
                build_region_scope(region)
            )
        except ValueError as exc:
            print(
                "[StrategicAgentScheduler] "
                "Skipping regional scope:",
                str(exc),
            )

    return scopes



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
            "last_material_changes": {},
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
                "No configured regional scopes."
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
                    f"{scope['region']}"
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

                if (
                    result.get("status") == "success"
                    and result.get("material_change", {}).get(
                        "material_change"
                    )
                ):
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
        job_key = f"{agent_key}:{scope['region']}"
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

                previous = load_latest_assessment(
                    agent_key=agent_key,
                    country_iso3=None,
                    region=scope.get("region"),
                )

                context = {
                    "country_iso3": None,
                    "country_name": None,
                    "region": scope.get("region"),
                    "regional_countries": scope.get(
                        "regional_countries",
                        [],
                    ),
                    "signals": [],
                    "regional_country_signal_limit": 6,
                    "regional_signal_limit": 60,
                    "timeframe": "180 days",
                }

                result = (
                    await strategic_agent_orchestrator.run_agent(
                        agent_key=agent_key,
                        context=context,
                        trigger_type="scheduled",
                    )
                )

                change_result = {
                    "material_change": False,
                    "reasons": [],
                }

                if result.get("status") == "success":
                    current = (
                        result.get("assessment")
                        or {}
                    )

                    assessment_promoted = bool(
                        (
                            result.get("run")
                            or {}
                        ).get(
                            "assessment_promoted",
                            True,
                        )
                    )

                    current_drivers = (
                        current.get("key_drivers") or []
                    )

                    current_is_insufficient = (
                        float(
                            current.get("risk_score") or 0
                        ) == 0
                        and float(
                            current.get("confidence") or 0
                        ) <= 30
                        and not current_drivers
                    )

                    previous_was_assessed = bool(
                        previous
                        and float(
                            previous.get("risk_score") or 0
                        ) > 0
                        and float(
                            previous.get("confidence") or 0
                        ) > 30
                    )

                    if not assessment_promoted:
                        change_result = {
                            "material_change": False,
                            "reasons": [
                                (
                                    result.get("run")
                                    or {}
                                ).get(
                                    "persistence_reason",
                                    "assessment_not_promoted",
                                )
                            ],
                            "score_delta": 0.0,
                            "confidence_delta": 0.0,
                            "previous_risk_level": (
                                previous.get("risk_level")
                                if previous
                                else None
                            ),
                            "current_risk_level": (
                                previous.get("risk_level")
                                if previous
                                else None
                            ),
                            "previous_direction": "preserved",
                            "current_direction": "preserved",
                            "new_critical_drivers": [],
                            "preserved_previous_assessment": True,
                        }

                        result["material_change"] = change_result

                        print(
                            "[StrategicAgentScheduler] "
                            "Skipping material-change detection "
                            "because assessment was not promoted:",
                            job_key,
                        )

                    elif (
                        current_is_insufficient
                        and previous_was_assessed
                    ):
                        change_result = {
                            "material_change": False,
                            "reasons": [
                                "evidence_collection_degraded"
                            ],
                            "score_delta": 0.0,
                            "confidence_delta": 0.0,
                            "previous_risk_level": (
                                previous.get("risk_level")
                            ),
                            "current_risk_level": (
                                previous.get("risk_level")
                            ),
                            "previous_direction": (
                                "preserved"
                            ),
                            "current_direction": (
                                "preserved"
                            ),
                            "previous_freshness": (
                                previous.get(
                                    "freshness_status"
                                )
                                or (
                                    previous.get(
                                        "presentation_payload"
                                    )
                                    or {}
                                ).get(
                                    "freshness_status"
                                )
                                or "unknown"
                            ),
                            "current_freshness": (
                                "data_degraded"
                            ),
                            "new_critical_drivers": [],
                            "preserved_previous_assessment": True,
                        }

                        result[
                            "material_change"
                        ] = change_result

                        print(
                            "[StrategicAgentScheduler] "
                            "Preserving previous assessment "
                            "because evidence collection "
                            "degraded:",
                            job_key,
                        )
                    else:
                        change_result = detect_material_change(
                            previous=previous,
                            current=current,
                        )

                    result["material_change"] = (
                        change_result
                    )

                    if change_result.get(
                        "material_change"
                    ):
                        self._state[
                            "last_material_changes"
                        ][job_key] = {
                            **change_result,
                            "checked_at": utc_now_iso(),
                        }
                    else:
                        self._state[
                            "last_material_changes"
                        ].pop(job_key, None)

                print(
                    "[StrategicAgentScheduler] Completed:",
                    job_key,
                    result.get("status"),
                    "material_change=",
                    change_result.get(
                        "material_change"
                    ),
                    "reasons=",
                    change_result.get("reasons"),
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
