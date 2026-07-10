"""Immutable Review Case v1 contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.review_runtime.privacy import metadata_to_dict, validate_safe_metadata

from ._validation import (
    CONTRACT_VERSION,
    check_keys,
    code,
    contract_version,
    enum_value,
    identifier,
    mapping,
    optional_identifier,
    positive_version,
    review_status,
    stage_name,
    timestamp,
)
from .enums import ReviewCaseType, ReviewPriority, ReviewStatus, SourceRuntime


@dataclass(frozen=True, slots=True)
class ReviewCase:
    review_case_id: str
    source_runtime: SourceRuntime | str
    source_stage: str
    source_artifact_id: str
    status: ReviewStatus | str
    reason_code: str
    priority: ReviewPriority | str
    created_at: str
    updated_at: str
    version: int
    metadata: Mapping[str, Any] = field(default_factory=dict)
    case_type: ReviewCaseType | str = ReviewCaseType.MANUAL_ESCALATION
    source_artifact_version: str | None = None
    parent_review_case_id: str | None = None
    correlation_id: str | None = None
    assigned_reviewer_id: str | None = None
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "review_case_id", identifier(self.review_case_id, ("review_case_id",)))
        object.__setattr__(self, "source_runtime", enum_value(self.source_runtime, SourceRuntime, ("source_runtime",)))
        object.__setattr__(self, "source_stage", stage_name(self.source_stage, ("source_stage",)))
        object.__setattr__(self, "source_artifact_id", identifier(self.source_artifact_id, ("source_artifact_id",)))
        object.__setattr__(self, "status", review_status(self.status, ("status",)))
        object.__setattr__(self, "reason_code", code(self.reason_code, ("reason_code",)))
        object.__setattr__(self, "priority", enum_value(self.priority, ReviewPriority, ("priority",)))
        object.__setattr__(self, "created_at", timestamp(self.created_at, ("created_at",)))
        object.__setattr__(self, "updated_at", timestamp(self.updated_at, ("updated_at",)))
        object.__setattr__(self, "version", positive_version(self.version, ("version",)))
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))
        object.__setattr__(self, "case_type", enum_value(self.case_type, ReviewCaseType, ("case_type",)))
        object.__setattr__(
            self,
            "source_artifact_version",
            optional_identifier(self.source_artifact_version, ("source_artifact_version",)),
        )
        object.__setattr__(
            self,
            "parent_review_case_id",
            optional_identifier(self.parent_review_case_id, ("parent_review_case_id",)),
        )
        object.__setattr__(self, "correlation_id", optional_identifier(self.correlation_id, ("correlation_id",)))
        object.__setattr__(
            self,
            "assigned_reviewer_id",
            optional_identifier(self.assigned_reviewer_id, ("assigned_reviewer_id",)),
        )
        object.__setattr__(
            self,
            "contract_version",
            contract_version(self.contract_version, ("contract_version",)),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReviewCase":
        data = mapping(payload)
        required = {
            "review_case_id",
            "source_runtime",
            "source_stage",
            "source_artifact_id",
            "status",
            "reason_code",
            "priority",
            "created_at",
            "updated_at",
            "version",
            "metadata",
        }
        allowed = required | {
            "case_type",
            "source_artifact_version",
            "parent_review_case_id",
            "correlation_id",
            "assigned_reviewer_id",
            "contract_version",
        }
        check_keys(data, allowed=allowed, required=required)
        return cls(
            review_case_id=data["review_case_id"],
            source_runtime=data["source_runtime"],
            source_stage=data["source_stage"],
            source_artifact_id=data["source_artifact_id"],
            status=data["status"],
            reason_code=data["reason_code"],
            priority=data["priority"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            version=data["version"],
            metadata=data["metadata"],
            case_type=data.get("case_type", ReviewCaseType.MANUAL_ESCALATION.value),
            source_artifact_version=data.get("source_artifact_version"),
            parent_review_case_id=data.get("parent_review_case_id"),
            correlation_id=data.get("correlation_id"),
            assigned_reviewer_id=data.get("assigned_reviewer_id"),
            contract_version=data.get("contract_version", CONTRACT_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "review_case_id": self.review_case_id,
            "case_type": self.case_type.value,
            "source_runtime": self.source_runtime.value,
            "source_stage": self.source_stage,
            "source_artifact_id": self.source_artifact_id,
            "source_artifact_version": self.source_artifact_version,
            "parent_review_case_id": self.parent_review_case_id,
            "correlation_id": self.correlation_id,
            "assigned_reviewer_id": self.assigned_reviewer_id,
            "status": self.status.value,
            "reason_code": self.reason_code,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "metadata": metadata_to_dict(self.metadata),
        }
