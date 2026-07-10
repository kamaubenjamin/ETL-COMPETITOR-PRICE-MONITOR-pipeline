"""Authoritative, dependency-light catalog of public workflow stage names."""

from __future__ import annotations

IMPLEMENTED_STAGE_TYPES = frozenset(
    {
        "document_ingest",
        "entity_extract",
        "transform",
        "filter",
        "fuzzy_match",
        "compare",
        "alert",
        "matching",
        "report",
        "validate_data",
    }
)

RESERVED_STAGE_TYPES = frozenset({"sort", "aggregate"})
WORKFLOW_STAGE_TYPES = IMPLEMENTED_STAGE_TYPES | RESERVED_STAGE_TYPES


def is_workflow_stage_type(stage_type: str) -> bool:
    return stage_type in WORKFLOW_STAGE_TYPES


def is_implemented_stage_type(stage_type: str) -> bool:
    return stage_type in IMPLEMENTED_STAGE_TYPES
