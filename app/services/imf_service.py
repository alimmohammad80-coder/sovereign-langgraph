from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx


IMF_BASE_URL = "https://www.imf.org/external/datamapper/api/v2"

IMF_INDICATORS = {
    "government_debt_pct_gdp": "GGXWDG_NGDP",
    "fiscal_balance_pct_gdp": "GGXCNL_NGDP",
    "current_account_pct_gdp": "BCA_NGDPD",
    "real_gdp_growth_pct": "NGDP_RPCH",
    "inflation_pct": "PCPIPCH",
}


def _year_status(year: int) -> str:
    current_year = datetime.now(timezone.utc).year

    if year < current_year:
        return "historical"
    if year == current_year:
        return "estimate"

    return "forecast"


async def fetch_imf_indicator(
    *,
    indicator_id: str,
    country_iso3: str,
) -> dict[str, Any]:
    iso3 = country_iso3.strip().upper()
    url = f"{IMF_BASE_URL}/{indicator_id}/{iso3}"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=15.0,
                write=10.0,
                pool=5.0,
            )
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

    except Exception as exc:
        return {
            "status": "error",
            "reason": str(exc),
            "indicator_id": indicator_id,
            "country_iso3": iso3,
            "observations": [],
        }

    raw_values = (
        payload.get("values", {})
        .get(indicator_id, {})
        .get(iso3, {})
    )

    observations: list[dict[str, Any]] = []

    for raw_year, raw_value in raw_values.items():
        try:
            year = int(raw_year)
            value = float(raw_value)
        except (TypeError, ValueError):
            continue

        observations.append(
            {
                "year": year,
                "value": value,
                "status": _year_status(year),
            }
        )

    observations.sort(
        key=lambda item: item["year"],
        reverse=True,
    )

    return {
        "status": "success",
        "indicator_id": indicator_id,
        "country_iso3": iso3,
        "observations": observations,
    }


async def get_imf_country_snapshot(
    country_iso3: str,
) -> dict[str, Any]:
    keys = list(IMF_INDICATORS)

    results = await asyncio.gather(
        *[
            fetch_imf_indicator(
                indicator_id=IMF_INDICATORS[key],
                country_iso3=country_iso3,
            )
            for key in keys
        ]
    )

    return {
        "source": "IMF",
        "country_iso3": country_iso3.strip().upper(),
        "series": dict(zip(keys, results, strict=True)),
    }
