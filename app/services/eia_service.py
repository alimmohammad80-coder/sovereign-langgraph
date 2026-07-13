from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx


EIA_BASE_URL = "https://api.eia.gov/v2"

EIA_SERIES: dict[str, dict[str, Any]] = {
    "wti_spot_price": {
        "route": "petroleum/pri/spt/data/",
        "frequency": "daily",
        "series": "RWTC",
        "limit": 10,
    },
    "brent_spot_price": {
        "route": "petroleum/pri/spt/data/",
        "frequency": "daily",
        "series": "RBRTE",
        "limit": 10,
    },
    "commercial_crude_stocks": {
        "route": "petroleum/stoc/wstk/data/",
        "frequency": "weekly",
        "series": "WCESTUS1",
        "limit": 10,
    },
    "us_crude_production": {
        "route": "petroleum/sum/sndw/data/",
        "frequency": "weekly",
        "series": "WCRFPUS2",
        "limit": 10,
    },
}


async def fetch_eia_series(
    *,
    route: str,
    frequency: str,
    series_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    api_key = os.getenv("EIA_API_KEY")

    if not api_key:
        return {
            "status": "unavailable",
            "reason": "missing_eia_api_key",
            "series_id": series_id,
            "observations": [],
        }

    url = f"{EIA_BASE_URL}/{route.lstrip('/')}"

    params = {
        "api_key": api_key,
        "frequency": frequency,
        "data[0]": "value",
        "facets[series][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": max(1, min(limit, 100)),
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=15.0,
                write=10.0,
                pool=5.0,
            )
        ) as client:
            response = await client.get(
                url,
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

    except Exception as exc:
        return {
            "status": "error",
            "reason": str(exc),
            "series_id": series_id,
            "observations": [],
        }

    rows = payload.get("response", {}).get("data", [])
    observations: list[dict[str, Any]] = []

    for row in rows:
        raw_value = row.get("value")

        if raw_value in (None, "", "."):
            continue

        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue

        observations.append(
            {
                "date": row.get("period"),
                "value": value,
                "units": row.get("units"),
                "description": (
                    row.get("series-description")
                    or row.get("seriesDescription")
                    or row.get("series")
                ),
            }
        )

    return {
        "status": "success",
        "series_id": series_id,
        "frequency": frequency,
        "observations": observations,
    }


async def get_eia_energy_snapshot() -> dict[str, Any]:
    keys = list(EIA_SERIES)

    results = await asyncio.gather(
        *[
            fetch_eia_series(
                route=EIA_SERIES[key]["route"],
                frequency=EIA_SERIES[key]["frequency"],
                series_id=EIA_SERIES[key]["series"],
                limit=EIA_SERIES[key]["limit"],
            )
            for key in keys
        ]
    )

    return {
        "source": "EIA",
        "series": dict(zip(keys, results, strict=True)),
    }
