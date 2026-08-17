from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd

from app.repositories.conflict_intelligence_repository import get_supabase_client


SOURCE_DIR = Path(
    "app/data/conflict_intelligence/source/"
    "ne_10m_admin_0_countries"
)

SHAPEFILE = SOURCE_DIR / "ne_10m_admin_0_countries.shp"
VERSION_FILE = SOURCE_DIR / "ne_10m_admin_0_countries.VERSION.txt"

OUTPUT = Path(
    "app/data/conflict_intelligence/border_dyads_seed.json"
)


def normalize_iso3(row) -> str | None:
    candidates = [
        row.get("ISO_A3_EH"),
        row.get("ISO_A3"),
        row.get("ADM0_A3"),
    ]

    for value in candidates:
        if not value:
            continue

        value = str(value).strip().upper()

        if len(value) == 3 and value != "-99":
            return value

    return None


def canonical_dyad(a: str, b: str) -> tuple[str, str, str]:
    country_a, country_b = sorted([
        a.strip().upper(),
        b.strip().upper(),
    ])

    dyad_id = f"DYAD-{country_a}-{country_b}-LAND"

    return country_a, country_b, dyad_id


def load_supported_iso3() -> set[str]:
    db = get_supabase_client()

    response = (
        db.table("conflict_countries")
        .select("iso3")
        .eq("active", True)
        .execute()
    )

    return {
        str(row["iso3"]).strip().upper()
        for row in (response.data or [])
        if row.get("iso3")
    }


def main() -> None:
    if not SHAPEFILE.exists():
        raise SystemExit(
            f"Natural Earth shapefile not found: {SHAPEFILE}"
        )

    supported_iso3 = load_supported_iso3()

    print(
        f"Conflict Intelligence countries: "
        f"{len(supported_iso3)}"
    )

    gdf = gpd.read_file(SHAPEFILE)

    gdf["ci_iso3"] = gdf.apply(
        normalize_iso3,
        axis=1,
    )

    gdf = gdf[
        gdf["ci_iso3"].isin(supported_iso3)
    ].copy()

    print(
        f"Natural Earth features matching registry: "
        f"{len(gdf)}"
    )

    # Multiple Natural Earth polygons/map units can resolve
    # to the same sovereign ISO3. Dissolve them first.
    countries = (
        gdf[["ci_iso3", "geometry"]]
        .dissolve(by="ci_iso3")
        .reset_index()
    )

    print(
        f"Unique supported geometries: "
        f"{len(countries)}"
    )

    sindex = countries.sindex

    dyads: dict[str, dict] = {}

    for idx, row in countries.iterrows():
        iso_a = row["ci_iso3"]
        geom_a = row.geometry

        if geom_a is None or geom_a.is_empty:
            continue

        candidate_indexes = list(
            sindex.query(
                geom_a,
                predicate="intersects",
            )
        )

        for other_idx in candidate_indexes:
            if other_idx <= idx:
                continue

            other = countries.iloc[other_idx]

            iso_b = other["ci_iso3"]
            geom_b = other.geometry

            if (
                iso_a == iso_b
                or geom_b is None
                or geom_b.is_empty
            ):
                continue

            # A genuine land border must share a LINE,
            # not merely touch at one point.
            shared_boundary = (
                geom_a.boundary
                .intersection(geom_b.boundary)
            )

            if shared_boundary.is_empty:
                continue

            if shared_boundary.length <= 1e-9:
                continue

            country_a, country_b, dyad_id = (
                canonical_dyad(
                    iso_a,
                    iso_b,
                )
            )

            dyads[dyad_id] = {
                "dyad_id": dyad_id,
                "country_a_iso3": country_a,
                "country_b_iso3": country_b,
                "dyad_type": "land",

                # Do not infer precise border length yet.
                "border_length_km": None,

                # Dispute status is a separate analytic layer.
                "disputed_flag": False,
                "dispute_name": None,
                "dispute_ref": None,

                "militarization_index": None,
                "trade_interdependence": None,
                "alliance_overlap": None,

                "geometry_ref": (
                    "Natural Earth "
                    "ne_10m_admin_0_countries"
                ),

                "active": True,

                "source": (
                    "Natural Earth "
                    "1:10m Admin-0 Countries"
                ),

                "source_version": None,

                "confidence_grade": "high",
                "review_status": "validated",
                "last_reviewed": (
                    datetime.now(timezone.utc)
                    .date()
                    .isoformat()
                ),
            }

    version = None

    if VERSION_FILE.exists():
        version = (
            VERSION_FILE
            .read_text()
            .strip()
        )

    for record in dyads.values():
        record["source_version"] = version

    records = sorted(
        dyads.values(),
        key=lambda x: x["dyad_id"],
    )

    payload = {
        "registry_name":
            "Conflict Intelligence Border Dyads",

        "registry_version":
            "conflict-border-dyads-v1",

        "generated_at":
            datetime.now(timezone.utc).isoformat(),

        "source_manifest": [
            {
                "source":
                    "Natural Earth "
                    "1:10m Admin-0 Countries",

                "version": version,

                "method":
                    "shared polygon boundary "
                    "after ISO3 normalization "
                    "and sovereign dissolve",
            }
        ],

        "record_count": len(records),
        "records": records,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
        )
    )

    print()
    print("=" * 70)
    print("CONFLICT INTELLIGENCE LAND DYADS")
    print("=" * 70)
    print(
        f"Supported countries: "
        f"{len(supported_iso3)}"
    )
    print(
        f"Land dyads generated: "
        f"{len(records)}"
    )
    print(
        f"Output: {OUTPUT}"
    )

    print()
    print("Sample dyads:")

    for row in records[:20]:
        print(
            row["dyad_id"]
        )


if __name__ == "__main__":
    main()
