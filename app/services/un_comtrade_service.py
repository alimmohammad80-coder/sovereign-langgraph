from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx


COMTRADE_URL = (
    "https://comtradeapi.un.org/"
    "public/v1/preview/C/A/HS"
)

REPORTER_CODES = {
    "IRN": "364",
}

FLOW_CODES = {
    "exports": "X",
    "imports": "M",
}


async def _request_with_retry(
    client: httpx.AsyncClient,
    *,
    params: dict[str, Any],
    max_attempts: int = 4,
) -> dict[str, Any]:
    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.get(
                COMTRADE_URL,
                params=params,
            )
        except Exception as exc:
            if attempt == max_attempts:
                return {
                    "status": "error",
                    "reason": str(exc),
                    "data": [],
                }

            await asyncio.sleep(attempt * 2)
            continue

        if response.status_code == 429:
            retry_after = response.headers.get(
                "Retry-After",
                "2",
            )

            try:
                delay = max(float(retry_after), 2.0)
            except ValueError:
                delay = 2.0

            if attempt == max_attempts:
                return {
                    "status": "rate_limited",
                    "reason": response.text[:500],
                    "data": [],
                }

            await asyncio.sleep(delay)
            continue

        if response.status_code != 200:
            return {
                "status": "error",
                "reason": (
                    f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                ),
                "data": [],
            }

        payload = response.json()

        return {
            "status": "success",
            "message": payload.get("message"),
            "data": payload.get("data", []),
        }

    return {
        "status": "error",
        "reason": "retry_loop_exhausted",
        "data": [],
    }


async def fetch_latest_total_trade(
    *,
    country_iso3: str,
    flow_name: str,
    lookback_years: int = 8,
) -> dict[str, Any]:
    iso3 = country_iso3.strip().upper()
    reporter_code = REPORTER_CODES.get(iso3)
    flow_code = FLOW_CODES.get(flow_name)

    if not reporter_code:
        return {
            "status": "unsupported",
            "reason": f"missing_reporter_code:{iso3}",
            "country_iso3": iso3,
            "flow": flow_name,
            "observation": None,
        }

    if not flow_code:
        return {
            "status": "error",
            "reason": f"invalid_flow:{flow_name}",
            "country_iso3": iso3,
            "flow": flow_name,
            "observation": None,
        }

    current_year = datetime.now(timezone.utc).year

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=5.0,
            read=25.0,
            write=10.0,
            pool=5.0,
        )
    ) as client:
        for year in range(
            current_year - 1,
            current_year - lookback_years - 1,
            -1,
        ):
            result = await _request_with_retry(
                client,
                params={
                    "reporterCode": reporter_code,
                    "period": str(year),
                    "partnerCode": "0",
                    "partner2Code": "0",
                    "cmdCode": "TOTAL",
                    "flowCode": flow_code,
                    "maxRecords": 20,
                    "breakdownMode": "classic",
                    "includeDesc": "true",
                },
            )

            if result["status"] != "success":
                if result["status"] == "rate_limited":
                    return {
                        **result,
                        "country_iso3": iso3,
                        "flow": flow_name,
                        "observation": None,
                    }

                continue

            rows = result.get("data", [])

            if rows:
                row = rows[0]

                try:
                    value = float(row.get("primaryValue"))
                except (TypeError, ValueError):
                    continue

                return {
                    "status": "success",
                    "country_iso3": iso3,
                    "flow": flow_name,
                    "observation": {
                        "year": year,
                        "value_usd": value,
                        "reporter": row.get("reporterDesc"),
                        "partner": row.get("partnerDesc"),
                        "flow_description": row.get("flowDesc"),
                        "commodity": row.get("cmdDesc"),
                    },
                }

            # Reduce the likelihood of a public-preview rate limit.
            await asyncio.sleep(1.25)

    return {
        "status": "unavailable",
        "reason": "no_trade_data_in_lookback_window",
        "country_iso3": iso3,
        "flow": flow_name,
        "observation": None,
    }


async def get_comtrade_country_snapshot(
    country_iso3: str,
) -> dict[str, Any]:
    # Run sequentially because the public endpoint is heavily rate-limited.
    exports = await fetch_latest_total_trade(
        country_iso3=country_iso3,
        flow_name="exports",
    )

    await asyncio.sleep(2.0)

    imports = await fetch_latest_total_trade(
        country_iso3=country_iso3,
        flow_name="imports",
    )

    return {
        "source": "UN Comtrade",
        "country_iso3": country_iso3.strip().upper(),
        "exports": exports,
        "imports": imports,
    }
