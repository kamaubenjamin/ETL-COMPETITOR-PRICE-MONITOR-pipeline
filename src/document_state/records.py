"""Immutable privacy-safe records for persistent Document State."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar

from .contracts import (
    DETERMINISTIC_ORDERING,
    DocumentStatus,
    DocumentType,
    MatchingStatus,
    OrderingSpec,
    Priority,
    ProcessingState,
    ReviewStatus,
    ValidationSeverity,
    WorkflowRunStatus,
)
from .privacy import (
    JsonScalar,
    bounded_string,
    confidence,
    enum_value,
    json_value,
    non_negative_count,
    optional_string,
    positive_version,
    stable_id,
    utc_timestamp,
    validate_safe_metadata,
)


class PersistentRecord:
    ORDERING: ClassVar[OrderingSpec]

    def to_dict(self) -> dict[str, Any]:
        return {item.name: json_value(getattr(self, item.name)) for item in fields(self)}


def _set_metadata(record: Any) -> None:
    object.__setattr__(record, "metadata", validate_safe_metadata(record.metadata))


@dataclass(frozen=True, slots=True)
class DocumentRecord(PersistentRecord):
    document_id: str
    filename: str
    document_type: DocumentType | str
    status: DocumentStatus | str
    confidence: float
    current_stage: str
    received_at: str
    created_at: str
    updated_at: str
    version: int = 1
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["document"]

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        object.__setattr__(self, "filename", bounded_string(self.filename, "filename"))
        object.__setattr__(self, "document_type", enum_value(self.document_type, DocumentType, "document_type"))
        object.__setattr__(self, "status", enum_value(self.status, DocumentStatus, "status"))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        object.__setattr__(self, "current_stage", bounded_string(self.current_stage, "current_stage", maximum=128))
        for name in ("received_at", "created_at", "updated_at"):
            object.__setattr__(self, name, utc_timestamp(getattr(self, name), name))
        object.__setattr__(self, "version", positive_version(self.version))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class DocumentLifecycleEvent(PersistentRecord):
    event_id: str
    document_id: str
    status: DocumentStatus | str
    occurred_at: str
    source_runtime: str
    source_stage: str
    reason_code: str | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["lifecycle_event"]

    def __post_init__(self) -> None:
        for name in ("event_id", "document_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "status", enum_value(self.status, DocumentStatus, "status"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        for name in ("source_runtime", "source_stage"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name, maximum=128))
        object.__setattr__(self, "reason_code", optional_string(self.reason_code, "reason_code", maximum=128))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class ProcessingSnapshot(PersistentRecord):
    snapshot_id: str
    document_id: str
    workflow_run_id: str
    stage: str
    status: ProcessingState | str
    started_at: str
    updated_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    version: int = 1
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["processing_snapshot"]

    def __post_init__(self) -> None:
        for name in ("snapshot_id", "document_id", "workflow_run_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "stage", bounded_string(self.stage, "stage", maximum=128))
        object.__setattr__(self, "status", enum_value(self.status, ProcessingState, "status"))
        object.__setattr__(self, "started_at", utc_timestamp(self.started_at, "started_at"))
        object.__setattr__(self, "updated_at", utc_timestamp(self.updated_at, "updated_at"))
        object.__setattr__(self, "completed_at", utc_timestamp(self.completed_at, "completed_at", optional=True))
        if self.duration_ms is not None:
            object.__setattr__(self, "duration_ms", non_negative_count(self.duration_ms, "duration_ms"))
        object.__setattr__(self, "version", positive_version(self.version))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class ValidationIssueRecord(PersistentRecord):
    issue_id: str
    document_id: str
    validation_run_id: str
    severity: ValidationSeverity | str
    field: str
    rule_id: str
    code: str
    message: str
    occurred_at: str
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["validation_issue"]

    def __post_init__(self) -> None:
        for name in ("issue_id", "document_id", "validation_run_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "severity", enum_value(self.severity, ValidationSeverity, "severity"))
        for name in ("field", "rule_id", "code"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name, maximum=128))
        object.__setattr__(self, "message", bounded_string(self.message, "message"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class MatchingSummaryRecord(PersistentRecord):
    match_id: str
    document_id: str
    matching_run_id: str
    entity_type: str
    candidate_id: str
    confidence: float
    status: MatchingStatus | str
    occurred_at: str
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["matching_summary"]

    def __post_init__(self) -> None:
        for name in ("match_id", "document_id", "matching_run_id", "candidate_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "entity_type", bounded_string(self.entity_type, "entity_type", maximum=128))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        object.__setattr__(self, "status", enum_value(self.status, MatchingStatus, "status"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class ReviewReferenceRecord(PersistentRecord):
    review_case_id: str
    document_id: str
    reason_code: str
    priority: Priority | str
    status: ReviewStatus | str
    created_at: str
    updated_at: str
    assigned_reviewer_id: str | None = None
    correction_count: int = 0
    decision_code: str | None = None
    reprocess_state: str | None = None
    version: int = 1
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["review_reference"]

    def __post_init__(self) -> None:
        for name in ("review_case_id", "document_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "reason_code", bounded_string(self.reason_code, "reason_code", maximum=128))
        object.__setattr__(self, "priority", enum_value(self.priority, Priority, "priority"))
        object.__setattr__(self, "status", enum_value(self.status, ReviewStatus, "status"))
        for name in ("created_at", "updated_at"):
            object.__setattr__(self, name, utc_timestamp(getattr(self, name), name))
        object.__setattr__(self, "assigned_reviewer_id", optional_string(self.assigned_reviewer_id, "assigned_reviewer_id", maximum=128))
        object.__setattr__(self, "correction_count", non_negative_count(self.correction_count, "correction_count"))
        for name in ("decision_code", "reprocess_state"):
            object.__setattr__(self, name, optional_string(getattr(self, name), name, maximum=128))
        object.__setattr__(self, "version", positive_version(self.version))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class CorrectionSummaryRecord(PersistentRecord):
    correction_id: str
    review_case_id: str
    document_id: str
    field_path: str
    operation: str
    reason_code: str
    actor_id: str
    occurred_at: str
    source_stage: str
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["correction_summary"]

    def __post_init__(self) -> None:
        for name in ("correction_id", "review_case_id", "document_id", "actor_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        for name in ("field_path", "operation", "reason_code", "source_stage"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name, maximum=128))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class ReprocessPlanRecord(PersistentRecord):
    plan_id: str
    review_case_id: str
    document_id: str
    requested_from_stage: str
    requested_target_stage: str
    invalidated_artifact_count: int
    retained_artifact_count: int
    reason_code: str
    requested_by: str
    created_at: str
    mode: str = "dry_run"
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["reprocess_plan"]

    def __post_init__(self) -> None:
        for name in ("plan_id", "review_case_id", "document_id", "requested_by"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        for name in ("requested_from_stage", "requested_target_stage", "reason_code", "mode"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name, maximum=128))
        for name in ("invalidated_artifact_count", "retained_artifact_count"):
            object.__setattr__(self, name, non_negative_count(getattr(self, name), name))
        object.__setattr__(self, "created_at", utc_timestamp(self.created_at, "created_at"))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class WorkflowRunRecord(PersistentRecord):
    run_id: str
    workflow_name: str
    status: WorkflowRunStatus | str
    started_at: str
    created_at: str
    updated_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    current_stage: str | None = None
    stage_count: int = 0
    succeeded_stage_count: int = 0
    failed_stage_count: int = 0
    version: int = 1
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["workflow_run"]

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", stable_id(self.run_id, "run_id"))
        object.__setattr__(self, "workflow_name", bounded_string(self.workflow_name, "workflow_name"))
        object.__setattr__(self, "status", enum_value(self.status, WorkflowRunStatus, "status"))
        for name in ("started_at", "created_at", "updated_at"):
            object.__setattr__(self, name, utc_timestamp(getattr(self, name), name))
        object.__setattr__(self, "completed_at", utc_timestamp(self.completed_at, "completed_at", optional=True))
        if self.duration_ms is not None:
            object.__setattr__(self, "duration_ms", non_negative_count(self.duration_ms, "duration_ms"))
        object.__setattr__(self, "current_stage", optional_string(self.current_stage, "current_stage", maximum=128))
        for name in ("stage_count", "succeeded_stage_count", "failed_stage_count"):
            object.__setattr__(self, name, non_negative_count(getattr(self, name), name))
        object.__setattr__(self, "version", positive_version(self.version))
        _set_metadata(self)


@dataclass(frozen=True, slots=True)
class AuditEventRecord(PersistentRecord):
    event_id: str
    event_type: str
    actor_id: str
    occurred_at: str
    document_id: str | None = None
    review_case_id: str | None = None
    workflow_run_id: str | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    ORDERING = DETERMINISTIC_ORDERING["audit_event"]

    def __post_init__(self) -> None:
        for name in ("event_id", "actor_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "event_type", bounded_string(self.event_type, "event_type", maximum=128))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        for name in ("document_id", "review_case_id", "workflow_run_id"):
            object.__setattr__(self, name, optional_string(getattr(self, name), name, maximum=128))
        _set_metadata(self)
