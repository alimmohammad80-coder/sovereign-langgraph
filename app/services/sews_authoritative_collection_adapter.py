from __future__ import annotations

import inspect
from dataclasses import asdict, is_dataclass
from typing import Any, Callable


def _serialize(value: Any) -> Any:
    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if is_dataclass(value):
        return asdict(value)

    if isinstance(value, dict):
        return {
            str(k): _serialize(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_serialize(v) for v in value]

    return value


def _records(value: Any) -> list[dict[str, Any]]:
    value = _serialize(value)

    if value is None:
        return []

    if isinstance(value, list):
        return [
            item if isinstance(item, dict) else {"value": item}
            for item in value
        ]

    if isinstance(value, dict):
        for key in (
            "signals",
            "data",
            "results",
            "records",
            "observations",
            "items",
        ):
            candidate = value.get(key)

            if isinstance(candidate, list):
                return [
                    item
                    if isinstance(item, dict)
                    else {"value": item}
                    for item in candidate
                ]

        return [value]

    return [{"value": value}]


async def _invoke(
    func: Callable[..., Any],
    *,
    query: str | None = None,
    limit: int = 5,
    country_iso3: str | None = None,
    region: str | None = None,
) -> list[dict[str, Any]]:
    """
    Call an existing Sovereign collector without imposing one fixed
    signature. Only parameters actually accepted by the collector are
    supplied.
    """
    signature = inspect.signature(func)
    parameters = signature.parameters

    candidates = {
        "query": query,
        "topic": query,
        "country_iso3": country_iso3,
        "iso3": country_iso3,
        "country": country_iso3,
        "region": region,
        "region_key": region,
        "limit": limit,
        "max_records": limit,
    }

    kwargs: dict[str, Any] = {}

    accepts_var_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in parameters.values()
    )

    for key, value in candidates.items():
        if value is None:
            continue

        if key in parameters or accepts_var_kwargs:
            kwargs[key] = value

    result = func(**kwargs)

    if inspect.isawaitable(result):
        result = await result

    return _records(result)


async def fetch_sews_economic_intelligence(
    query: str | None = None,
    limit: int = 5,
    country_iso3: str | None = None,
    region: str | None = None,
):
    from app.services.strategic_agents.live_economic_collector import (
        collect_live_economic_signals,
    )

    return await _invoke(
        collect_live_economic_signals,
        query=query,
        limit=limit,
        country_iso3=country_iso3,
        region=region,
    )


async def fetch_sews_energy_intelligence(
    query: str | None = None,
    limit: int = 5,
    country_iso3: str | None = None,
    region: str | None = None,
):
    from app.services.strategic_agents.live_energy_collector import (
        collect_live_energy_signals,
    )

    return await _invoke(
        collect_live_energy_signals,
        query=query,
        limit=limit,
        country_iso3=country_iso3,
        region=region,
    )


async def fetch_sews_conflict_intelligence(
    query: str | None = None,
    limit: int = 5,
    country_iso3: str | None = None,
    region: str | None = None,
):
    from app.services.strategic_agents.live_conflict_collector import (
        collect_live_conflict_signals,
    )

    return await _invoke(
        collect_live_conflict_signals,
        query=query,
        limit=limit,
        country_iso3=country_iso3,
        region=region,
    )


async def fetch_sews_political_intelligence(
    query: str | None = None,
    limit: int = 5,
    country_iso3: str | None = None,
    region: str | None = None,
):
    from app.services.strategic_agents.live_political_collector import (
        collect_live_political_signals,
    )

    return await _invoke(
        collect_live_political_signals,
        query=query,
        limit=limit,
        country_iso3=country_iso3,
        region=region,
    )


async def fetch_sews_trade_sanctions_intelligence(
    query: str | None = None,
    limit: int = 5,
    country_iso3: str | None = None,
    region: str | None = None,
):
    from app.services.strategic_agents.live_trade_sanctions_collector import (
        collect_live_trade_sanctions_signals,
    )

    return await _invoke(
        collect_live_trade_sanctions_signals,
        query=query,
        limit=limit,
        country_iso3=country_iso3,
        region=region,
    )
