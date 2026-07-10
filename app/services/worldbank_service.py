from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2"


INDICATORS = {
    "gdp_current_usd": "NY.GDP.MKTP.CD",
    "gdp_growth_pct": "NY.GDP.MKTP.KD.ZG",
    "inflation_pct": "FP.CPI.TOTL.ZG",
    "unemployment_pct": "SL.UEM.TOTL.ZS",
    "government_debt_pct_gdp": "GC.DOD.TOTL.GD.ZS",
    "current_account_pct_gdp": "BN.CAB.XOKA.GD.ZS",
    "foreign_reserves_usd": "FI.RES.TOTL.CD",
    "trade_pct_gdp": "NE.TRD.GNFS.ZS",
}


@dataclass
class WorldBankObservation:
    indicator_key: str
    indicator_code: str
    value: float
    year: int
    country_code: str
    country_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "indicator_key": self.indicator_key,
            "indicator_code": self.indicator_code,
            "value": self.value,
            "year": self.year,
            "country_code": self.country_code,
            "country_name": self.country_name,
        }


async def _fetch_indicator(
    *,
    country_code: str,
    indicator_key: str,
    indicator_code: str,
    years: int = 8,
) -> list[WorldBankObservation]:
    url = (
        f"{WORLD_BANK_BASE_URL}/country/{country_code}/indicator/"
        f"{indicator_code}"
    )

    params = {
        "format": "json",
        "per_page": 100,
        "date": f"{2026 - years}:2026",
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, list) or len(payload) < 2:
        return []

    rows = payload[1] or []
    observations: list[WorldBankObservation] = []

    for row in rows:
        value = row.get("value")
        year = row.get("date")

        if value is None or year is None:
            continue

        try:
            observations.append(
                WorldBankObservation(
                    indicator_key=indicator_key,
                    indicator_code=indicator_code,
                    value=float(value),
                    year=int(year),
                    country_code=str(row.get("countryiso3code") or country_code),
                    country_name=str(
                        (row.get("country") or {}).get("value")
                        or country_code
                    ),
                )
            )
        except (TypeError, ValueError):
            continue

    return sorted(
        observations,
        key=lambda item: item.year,
        reverse=True,
    )


async def get_country_macro_snapshot(
    *,
    country_code: str,
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "country_code": country_code.upper(),
        "indicators": {},
        "source": "World Bank",
    }

    for indicator_key, indicator_code in INDICATORS.items():
        try:
            observations = await _fetch_indicator(
                country_code=country_code,
                indicator_key=indicator_key,
                indicator_code=indicator_code,
            )
        except Exception as exc:
            snapshot["indicators"][indicator_key] = {
                "status": "error",
                "indicator_code": indicator_code,
                "message": str(exc),
                "latest": None,
                "history": [],
            }
            continue

        snapshot["indicators"][indicator_key] = {
            "status": "success" if observations else "empty",
            "indicator_code": indicator_code,
            "latest": (
                observations[0].to_dict()
                if observations
                else None
            ),
            "history": [
                observation.to_dict()
                for observation in observations
            ],
        }

    return snapshot
