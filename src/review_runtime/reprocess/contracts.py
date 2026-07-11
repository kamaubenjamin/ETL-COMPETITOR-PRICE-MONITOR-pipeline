"""Neutral dry-run reprocess plan contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.review_runtime.contracts._validation import (
    CONTRACT_VERSION,
    check_keys,
    code,
    contract_version,
    identifier,
    mapping,
    stage_name,
    string_tuple,
    timestamp,
)
from src.review_runtime.errors import INVALID_VALUE, ReviewRuntimeError
from src.review_runtime.privacy import metadata_to_dict, validate_safe_metadata

# This dependency-free mirror is the Phase 4 handoff seam. Workflow Runtime
# remains authoritative for execution and must validate a plan again before use.
SAFE_REPROCESS_STAGE_ORDER = (
    "document_ingest",
    "entity_extract",
    "transform",
    "validate_data",
    "filter",
    "sort",
    "aggregate",
    "matching",
    "fuzzy_match",
    "compare",
    "alert",
    "report",
)
SAFE_REPROCESS_STAGES = frozenset(SAFE_REPROCESS_STAGE_ORDER)


def _artifact_ids(value: Any, path: tuple[str | int, ...]) -> tuple[str, ...]:
    values = string_tuple(value, path, max_items=100)
    return tuple(sorted(values))


@dataclass(frozen=True, slots=True)
class ReprocessPlan:
    plan_id: str
    review_case_id: str
    requested_from_stage: str
    requested_target_stage: str
    invalidated_artifacts: tuple[str, ...]
    retained_artifacts: tuple[str, ...]
    reason_code: str
    requested_by: str
    created_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", identifier(self.plan_id, ("plan_id",)))
        object.__setattr__(self, "review_case_id", identifier(self.review_case_id, ("review_case_id",)))
        from_stage = stage_name(self.requested_from_stage, ("requested_from_stage",))
        target_stage = stage_name(self.requested_target_stage, ("requested_target_stage",))
        if from_stage not in SAFE_REPROCESS_STAGES:
            raise ReviewRuntimeError(INVALID_VALUE, "Unknown requested_from_stage code.", ("requested_from_stage",))
        if target_stage not in SAFE_REPROCESS_STAGES:
            raise ReviewRuntimeError(INVALID_VALUE, "Unknown requested_target_stage code.", ("requested_target_stage",))
        object.__setattr__(self, "requested_from_stage", from_stage)
        object.__setattr__(self, "requested_target_stage", target_stage)
        invalidated = _artifact_ids(self.invalidated_artifacts, ("invalidated_artifacts",))
        retained = _artifact_ids(self.retained_artifacts, ("retained_artifacts",))
        if not invalidated:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "At least one invalidated artifact identifier is required.",
                ("invalidated_artifacts",),
            )
        if set(invalidated) & set(retained):
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "Invalidated and retained artifact identifiers must be disjoint.",
                ("retained_artifacts",),
            )
        object.__setattr__(self, "invalidated_artifacts", invalidated)
        object.__setattr__(self, "retained_artifacts", retained)
        object.__setattr__(self, "reason_code", code(self.reason_code, ("reason_code",)))
        object.__setattr__(self, "requested_by", identifier(self.requested_by, ("requested_by",)))
        object.__setattr__(self, "created_at", timestamp(self.created_at, ("created_at",)))
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))
        if self.dry_run is not True:
            raise ReviewRuntimeError(INVALID_VALUE, "Reprocess plans must be dry-run only.", ("dry_run",))
        object.__setattr__(self, "contract_version", contract_version(self.contract_version, ("contract_version",)))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReprocessPlan":
        data = mapping(payload)
        required = {
            "plan_id", "review_case_id", "requested_from_stage", "requested_target_stage",
            "invalidated_artifacts", "retained_artifacts", "reason_code", "requested_by",
            "created_at", "metadata",
        }
        allowed = required | {"dry_run", "contract_version"}
        check_keys(data, allowed=allowed, required=required)
        return cls(
            plan_id=data["plan_id"],
            review_case_id=data["review_case_id"],
            requested_from_stage=data["requested_from_stage"],
            requested_target_stage=data["requested_target_stage"],
            invalidated_artifacts=tuple(data["invalidated_artifacts"]),
            retained_artifacts=tuple(data["retained_artifacts"]),
            reason_code=data["reason_code"],
            requested_by=data["requested_by"],
            created_at=data["created_at"],
            metadata=data["metadata"],
            dry_run=data.get("dry_run", True),
            contract_version=data.get("contract_version", CONTRACT_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "plan_id": self.plan_id,
            "review_case_id": self.review_case_id,
            "requested_from_stage": self.requested_from_stage,
            "requested_target_stage": self.requested_target_stage,
            "invalidated_artifacts": list(self.invalidated_artifacts),
            "retained_artifacts": list(self.retained_artifacts),
            "reason_code": self.reason_code,
            "requested_by": self.requested_by,
            "created_at": self.created_at,
            "metadata": metadata_to_dict(self.metadata),
            "dry_run": self.dry_run,
        }

