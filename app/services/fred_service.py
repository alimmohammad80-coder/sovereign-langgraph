from __future__ import annotations

import os
from typing import Any

import httpx


FRED_BASE_URL = (
    "https://api.stlouisfed.org/fred/series/observations"
)

FRED_SERIES = {
    "wti_crude_usd": "DCOILWTICO",
    "brent_crude_usd": "DCOILBRENTEU",
    "broad_usd_index": "DTWEXBGS",
    "federal_funds_rate": "DFF",
    "vix_index": "VIXCLS",
}


async def fetch_fred_series(
    *,
    series_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    api_key = os.getenv("FRED_API_KEY")

    if not api_key:
        return {
            "status": "unavailable",
            "reason": "missing_fred_api_key",
            "series_id": series_id,
            "observations": [],
        }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=4.0,
                read=8.0,
                write=8.0,
                pool=4.0,
            )
        ) as client:
            response = await client.get(
                FRED_BASE_URL,
                params={
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": max(1, min(limit, 100)),
                },
            )
            response.raise_for_status()

    except Exception as exc:
        return {
            "status": "error",
            "reason": str(exc),
            "series_id": series_id,
            "observations": [],
        }

    observations = []

    for item in response.json().get("observations", []):
        raw_value = item.get("value")

        if raw_value in (None, "", "."):
            continue

        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue

        observations.append(
            {
                "date": item.get("date"),
                "value": value,
            }
        )

    return {
        "status": "success",
        "series_id": series_id,
        "observations": observations,
    }


async def get_fred_market_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "source": "FRED",
        "series": {},
    }

    for key, series_id in FRED_SERIES.items():
        snapshot["series"][key] = await fetch_fred_series(
            series_id=series_id,
            limit=10,
        )

    return snapshot
