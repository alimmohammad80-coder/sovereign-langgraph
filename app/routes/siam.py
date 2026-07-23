from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.siam.fusion import siam_fusion_engine
from app.services.strategic_reporting_service import (
    _build_regional_packet,
)


router = APIRouter(
    prefix="/api/siam",
    tags=["SIAM"],
)


@router.get("/regional/{region}")
def get_regional_strategic_intelligence(
    region: str,
):
    try:
        clean_region = " ".join(
            str(region or "").strip().split()
        )

        if not clean_region:
            raise ValueError("A region is required.")

        packet = _build_regional_packet(
            region=clean_region,
        )

        assessments = packet.get(
            "sector_assessments",
            [],
        )

        if not assessments:
            raise ValueError(
                f"No authoritative assessments found for {clean_region}."
            )

        result = siam_fusion_engine.fuse(
            region=clean_region,
            assessments=assessments,
        )

        return {
            "status": "success",
            "data": result.to_dict(),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "SIAM regional fusion failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc
