from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SEWSInitializeRequest(BaseModel):
    seed_indicator_definitions: bool = True
    load_warning_indicator_mappings: bool = True
    active_only: bool = True
    dry_run: bool = False


class SEWSInitializeResponse(BaseModel):
    status: str
    dry_run: bool
    indicator_definitions_in_library: int
    mapping_references_in_frameworks: int
    unique_warning_indicator_pairs: int
    missing_warning_problems: list[str] = Field(default_factory=list)
    indicator_definitions_upserted: int = 0
    mappings_upserted: int = 0
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SEWSRuntimeStatusResponse(BaseModel):
    warning_problems: int
    indicator_definitions: int
    warning_indicator_mappings: int
    mapped_warning_problems: int
    unmapped_warning_problems: list[str] = Field(default_factory=list)
    mapping_ready: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
