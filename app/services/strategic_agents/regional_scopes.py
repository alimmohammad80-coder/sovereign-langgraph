from __future__ import annotations

from typing import Any


REGIONAL_SCOPES: dict[str, list[dict[str, str]]] = {
    "Middle East": [
        {"country_iso3": "IRN", "country_name": "Iran"},
        {"country_iso3": "IRQ", "country_name": "Iraq"},
        {"country_iso3": "SAU", "country_name": "Saudi Arabia"},
        {"country_iso3": "ARE", "country_name": "United Arab Emirates"},
        {"country_iso3": "ISR", "country_name": "Israel"},
        {"country_iso3": "TUR", "country_name": "Türkiye"},
        {"country_iso3": "EGY", "country_name": "Egypt"},
        {"country_iso3": "YEM", "country_name": "Yemen"},
        {"country_iso3": "JOR", "country_name": "Jordan"},
        {"country_iso3": "LBN", "country_name": "Lebanon"},
        {"country_iso3": "QAT", "country_name": "Qatar"},
        {"country_iso3": "OMN", "country_name": "Oman"},
    ],
    "Europe": [
        {"country_iso3": "GBR", "country_name": "United Kingdom"},
        {"country_iso3": "FRA", "country_name": "France"},
        {"country_iso3": "DEU", "country_name": "Germany"},
        {"country_iso3": "ITA", "country_name": "Italy"},
        {"country_iso3": "POL", "country_name": "Poland"},
        {"country_iso3": "UKR", "country_name": "Ukraine"},
        {"country_iso3": "ROU", "country_name": "Romania"},
        {"country_iso3": "SWE", "country_name": "Sweden"},
    ],
    "Eurasia": [
        {"country_iso3": "RUS", "country_name": "Russia"},
        {"country_iso3": "BLR", "country_name": "Belarus"},
        {"country_iso3": "ARM", "country_name": "Armenia"},
        {"country_iso3": "AZE", "country_name": "Azerbaijan"},
        {"country_iso3": "GEO", "country_name": "Georgia"},
    ],
    "Central Asia": [
        {"country_iso3": "KAZ", "country_name": "Kazakhstan"},
        {"country_iso3": "UZB", "country_name": "Uzbekistan"},
        {"country_iso3": "TKM", "country_name": "Turkmenistan"},
        {"country_iso3": "KGZ", "country_name": "Kyrgyzstan"},
        {"country_iso3": "TJK", "country_name": "Tajikistan"},
    ],
    "South Asia": [
        {"country_iso3": "AFG", "country_name": "Afghanistan"},
        {"country_iso3": "PAK", "country_name": "Pakistan"},
        {"country_iso3": "IND", "country_name": "India"},
        {"country_iso3": "BGD", "country_name": "Bangladesh"},
        {"country_iso3": "LKA", "country_name": "Sri Lanka"},
        {"country_iso3": "NPL", "country_name": "Nepal"},
    ],
    "East Asia": [
        {"country_iso3": "CHN", "country_name": "China"},
        {"country_iso3": "JPN", "country_name": "Japan"},
        {"country_iso3": "KOR", "country_name": "South Korea"},
        {"country_iso3": "PRK", "country_name": "North Korea"},
        {"country_iso3": "MNG", "country_name": "Mongolia"},
        {"country_iso3": "TWN", "country_name": "Taiwan"},
    ],
    "Southeast Asia": [
        {"country_iso3": "IDN", "country_name": "Indonesia"},
        {"country_iso3": "VNM", "country_name": "Vietnam"},
        {"country_iso3": "PHL", "country_name": "Philippines"},
        {"country_iso3": "THA", "country_name": "Thailand"},
        {"country_iso3": "MYS", "country_name": "Malaysia"},
        {"country_iso3": "SGP", "country_name": "Singapore"},
        {"country_iso3": "MMR", "country_name": "Myanmar"},
    ],
    "Sub-Saharan Africa": [
        {"country_iso3": "NGA", "country_name": "Nigeria"},
        {"country_iso3": "ZAF", "country_name": "South Africa"},
        {"country_iso3": "ETH", "country_name": "Ethiopia"},
        {"country_iso3": "KEN", "country_name": "Kenya"},
        {"country_iso3": "SDN", "country_name": "Sudan"},
        {"country_iso3": "COD", "country_name": "DR Congo"},
        {"country_iso3": "SOM", "country_name": "Somalia"},
    ],
    "North America": [
        {"country_iso3": "USA", "country_name": "United States"},
        {"country_iso3": "CAN", "country_name": "Canada"},
        {"country_iso3": "MEX", "country_name": "Mexico"},
    ],
    "Latin America and Caribbean": [
        {"country_iso3": "BRA", "country_name": "Brazil"},
        {"country_iso3": "ARG", "country_name": "Argentina"},
        {"country_iso3": "COL", "country_name": "Colombia"},
        {"country_iso3": "VEN", "country_name": "Venezuela"},
        {"country_iso3": "CHL", "country_name": "Chile"},
        {"country_iso3": "PER", "country_name": "Peru"},
        {"country_iso3": "CUB", "country_name": "Cuba"},
    ],
}


def normalize_region(value: str | None) -> str:
    return " ".join(
        str(value or "").strip().split()
    )


def get_region_countries(
    region: str,
) -> list[dict[str, str]]:
    requested = normalize_region(region).lower()

    for canonical, countries in REGIONAL_SCOPES.items():
        if canonical.lower() == requested:
            return [
                {
                    **country,
                    "region": canonical,
                }
                for country in countries
            ]

    return []


def build_region_scope(
    region: str,
) -> dict[str, Any]:
    canonical = normalize_region(region)
    countries = get_region_countries(canonical)

    if not countries:
        raise ValueError(
            f"Unknown or empty regional scope: {region}"
        )

    return {
        "region": countries[0]["region"],
        "regional_countries": countries,
    }
