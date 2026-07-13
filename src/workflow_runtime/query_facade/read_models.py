"""Immutable privacy-safe read models exposed by Workflow Query Facade."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from datetime import datetime
import math
from types import MappingProxyType
from typing import Any, ClassVar

from .contracts import (
    DocumentStatus,
    DocumentType,
    OrderingSpec,
    Priority,
    ReviewStatus,
    SortDirection,
    WorkflowStatus,
    bounded_string,
    enum_value,
)


_UNSAFE_METADATA_TOKENS = {
    "content", "credential", "document", "exception", "payload", "raw", "row",
    "secret", "stack", "storage", "token", "traceback", "value",
}


def _timestamp(value: str | None, field_name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    safe = bounded_string(value, field_name, maximum=64)
    try:
        parsed = datetime.fromisoformat(safe.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return safe


def _optional_string(value: str | None, field_name: str, *, maximum: int = 256) -> str | None:
    return None if value is None else bounded_string(value, field_name, maximum=maximum)


def _confidence(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("confidence must be a finite number between 0 and 1")
    return float(value)


def _count(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _safe_metadata(value: Mapping[str, Any]) -> Mapping[str, str | int | bool | None]:
    if not isinstance(value, Mapping) or len(value) > 20:
        raise ValueError("metadata must be a bounded mapping")
    safe: dict[str, str | int | bool | None] = {}
    for key, item in value.items():
        safe_key = bounded_string(key, "metadata key", maximum=64)
        tokens = set(safe_key.lower().replace("-", "_").split("_"))
        if tokens & _UNSAFE_METADATA_TOKENS:
            raise ValueError("metadata key is not allowlisted")
        if item is not None and not isinstance(item, (str, int, bool)):
            raise ValueError("metadata values must be JSON scalar values")
        if isinstance(item, str) and len(item) > 128:
            raise ValueError("metadata string values must be bounded")
        safe[safe_key] = item
    return MappingProxyType(safe)


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise ValueError("read model contains non-JSON data")


class ReadModel:
    ORDERING: ClassVar[OrderingSpec]

    def to_dict(self) -> dict[str, Any]:
        return {item.name: _json_value(getattr(self, item.name)) for item in fields(self)}


@dataclass(frozen=True, slots=True)
class DocumentInboxItem(ReadModel):
    document_id: str
    filename: str
    document_type: DocumentType | str
    status: DocumentStatus | str
    confidence: float
    current_stage: str
    received_at: str
    tenant_id: str = "tenant-local"

    ORDERING = OrderingSpec(("received_at", "document_id"), (SortDirection.ASCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", bounded_string(self.document_id, "document_id"))
        object.__setattr__(self, "filename", bounded_string(self.filename, "filename"))
        object.__setattr__(self, "document_type", enum_value(self.document_type, DocumentType, "document_type"))
        object.__setattr__(self, "status", enum_value(self.status, DocumentStatus, "status"))
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        object.__setattr__(self, "current_stage", bounded_string(self.current_stage, "current_stage", maximum=128))
        object.__setattr__(self, "received_at", _timestamp(self.received_at, "received_at"))
        object.__setattr__(self, "tenant_id", bounded_string(self.tenant_id, "tenant_id", maximum=128))


@dataclass(frozen=True, slots=True)
class DocumentDetail(ReadModel):
    document_id: str
    filename: str
    document_type: DocumentType | str
    status: DocumentStatus | str
    confidence: float
    current_stage: str
    received_at: str
    updated_at: str
    workflow_name: str | None = None
    tenant_id: str = "tenant-local"

    ORDERING = OrderingSpec(("document_id",), (SortDirection.ASCENDING,))

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", bounded_string(self.document_id, "document_id"))
        object.__setattr__(self, "filename", bounded_string(self.filename, "filename"))
        object.__setattr__(self, "document_type", enum_value(self.document_type, DocumentType, "document_type"))
        object.__setattr__(self, "status", enum_value(self.status, DocumentStatus, "status"))
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        object.__setattr__(self, "current_stage", bounded_string(self.current_stage, "current_stage", maximum=128))
        object.__setattr__(self, "received_at", _timestamp(self.received_at, "received_at"))
        object.__setattr__(self, "updated_at", _timestamp(self.updated_at, "updated_at"))
        object.__setattr__(self, "workflow_name", _optional_string(self.workflow_name, "workflow_name"))
        object.__setattr__(self, "tenant_id", bounded_string(self.tenant_id, "tenant_id", maximum=128))


@dataclass(frozen=True, slots=True)
class ProcessingStatus(ReadModel):
    document_id: str
    stage: str
    status: str
    occurred_at: str

    ORDERING = OrderingSpec(("occurred_at", "stage"), (SortDirection.ASCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", bounded_string(self.document_id, "document_id"))
        object.__setattr__(self, "stage", bounded_string(self.stage, "stage", maximum=128))
        object.__setattr__(self, "status", bounded_string(self.status, "status", maximum=64))
        object.__setattr__(self, "occurred_at", _timestamp(self.occurred_at, "occurred_at"))


@dataclass(frozen=True, slots=True)
class ValidationIssue(ReadModel):
    issue_id: str
    document_id: str
    severity: str
    field: str
    rule_id: str
    code: str
    message: str

    ORDERING = OrderingSpec(("severity", "field", "rule_id", "issue_id"), (SortDirection.DESCENDING, SortDirection.ASCENDING, SortDirection.ASCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        for name in ("issue_id", "document_id", "field", "rule_id", "code"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name))
        if self.severity not in {"warning", "error"}:
            raise ValueError("severity is invalid")
        object.__setattr__(self, "message", bounded_string(self.message, "message", maximum=256))


@dataclass(frozen=True, slots=True)
class MatchingResult(ReadModel):
    match_id: str
    document_id: str
    entity_type: str
    candidate_id: str
    confidence: float
    status: str

    ORDERING = OrderingSpec(("confidence", "candidate_id", "match_id"), (SortDirection.DESCENDING, SortDirection.ASCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        for name in ("match_id", "document_id", "entity_type", "candidate_id"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name))
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        if self.status not in {"candidate", "matched", "ambiguous", "no_match"}:
            raise ValueError("status is invalid")


@dataclass(frozen=True, slots=True)
class ReviewCaseSummary(ReadModel):
    review_case_id: str
    document_id: str
    reason_code: str
    priority: Priority | str
    status: ReviewStatus | str
    assigned_reviewer_id: str | None
    correction_count: int
    decision_code: str | None
    reprocess_state: str
    created_at: str
    updated_at: str

    ORDERING = OrderingSpec(("created_at", "review_case_id"), (SortDirection.ASCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        for name in ("review_case_id", "document_id", "reason_code"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name))
        object.__setattr__(self, "priority", enum_value(self.priority, Priority, "priority"))
        object.__setattr__(self, "status", enum_value(self.status, ReviewStatus, "status"))
        object.__setattr__(self, "assigned_reviewer_id", _optional_string(self.assigned_reviewer_id, "assigned_reviewer_id"))
        object.__setattr__(self, "correction_count", _count(self.correction_count, "correction_count"))
        object.__setattr__(self, "decision_code", _optional_string(self.decision_code, "decision_code", maximum=64))
        if self.reprocess_state not in {"not_requested", "requested", "planned"}:
            raise ValueError("reprocess_state is invalid")
        object.__setattr__(self, "created_at", _timestamp(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _timestamp(self.updated_at, "updated_at"))


@dataclass(frozen=True, slots=True)
class CorrectionHistorySummary(ReadModel):
    correction_id: str
    review_case_id: str
    field_path: str
    operation: str
    reason_code: str
    actor_id: str
    occurred_at: str
    source_stage: str

    ORDERING = OrderingSpec(("occurred_at", "correction_id"), (SortDirection.ASCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        for name in ("correction_id", "review_case_id", "field_path", "operation", "reason_code", "actor_id", "source_stage"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name))
        object.__setattr__(self, "occurred_at", _timestamp(self.occurred_at, "occurred_at"))


@dataclass(frozen=True, slots=True)
class ReprocessPlanSummary(ReadModel):
    plan_id: str
    review_case_id: str
    requested_from_stage: str
    requested_target_stage: str
    invalidated_artifact_count: int
    retained_artifact_count: int
    reason_code: str
    requested_by: str
    created_at: str
    mode: str = "dry_run"

    ORDERING = OrderingSpec(("created_at", "plan_id"), (SortDirection.ASCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        for name in ("plan_id", "review_case_id", "requested_from_stage", "requested_target_stage", "reason_code", "requested_by"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name))
        object.__setattr__(self, "invalidated_artifact_count", _count(self.invalidated_artifact_count, "invalidated_artifact_count"))
        object.__setattr__(self, "retained_artifact_count", _count(self.retained_artifact_count, "retained_artifact_count"))
        object.__setattr__(self, "created_at", _timestamp(self.created_at, "created_at"))
        if self.mode != "dry_run":
            raise ValueError("mode must be dry_run")


@dataclass(frozen=True, slots=True)
class WorkflowRunSummary(ReadModel):
    run_id: str
    workflow_name: str
    status: WorkflowStatus | str
    started_at: str
    completed_at: str | None
    duration_ms: int | None
    stage_count: int = 0
    completed_stage_count: int = 0
    failed_stage_count: int = 0

    ORDERING = OrderingSpec(("started_at", "run_id"), (SortDirection.DESCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", bounded_string(self.run_id, "run_id"))
        object.__setattr__(self, "workflow_name", bounded_string(self.workflow_name, "workflow_name"))
        object.__setattr__(self, "status", enum_value(self.status, WorkflowStatus, "status"))
        object.__setattr__(self, "started_at", _timestamp(self.started_at, "started_at"))
        object.__setattr__(self, "completed_at", _timestamp(self.completed_at, "completed_at", optional=True))
        if self.duration_ms is not None:
            object.__setattr__(self, "duration_ms", _count(self.duration_ms, "duration_ms"))
        for name in ("stage_count", "completed_stage_count", "failed_stage_count"):
            object.__setattr__(self, name, _count(getattr(self, name), name))
        if self.completed_stage_count + self.failed_stage_count > self.stage_count:
            raise ValueError("stage counts are inconsistent")


@dataclass(frozen=True, slots=True)
class AuditEventSummary(ReadModel):
    event_id: str
    event_type: str
    actor_id: str
    occurred_at: str
    document_id: str | None = None
    review_case_id: str | None = None
    metadata: Mapping[str, str | int | bool | None] = field(default_factory=lambda: MappingProxyType({}))

    ORDERING = OrderingSpec(("occurred_at", "event_id"), (SortDirection.DESCENDING, SortDirection.ASCENDING))

    def __post_init__(self) -> None:
        for name in ("event_id", "event_type", "actor_id"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name))
        object.__setattr__(self, "occurred_at", _timestamp(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "document_id", _optional_string(self.document_id, "document_id"))
        object.__setattr__(self, "review_case_id", _optional_string(self.review_case_id, "review_case_id"))
        object.__setattr__(self, "metadata", _safe_metadata(self.metadata))
