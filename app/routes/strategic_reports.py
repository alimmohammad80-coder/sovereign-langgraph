from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.strategic_reporting_service import (
    generate_regional_report,
)


router = APIRouter(
    prefix="/api/strategic-reports",
    tags=["Strategic Intelligence Reports"],
)


class RegionalReportRequest(BaseModel):
    region: str

    report_type: Literal[
        "short_term",
        "long_term_fusion",
    ] = "short_term"


@router.post("/generate")
def generate_report(
    payload: RegionalReportRequest,
):
    try:
        return generate_regional_report(
            region=payload.region,
            report_type=payload.report_type,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Regional report generation failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc
