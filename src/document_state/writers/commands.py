"""Immutable, runtime-neutral commands for Document State writers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
import re
from typing import Any

from ..contracts import (
    DocumentStatus,
    DocumentType,
    MatchingStatus,
    Priority,
    ProcessingState,
    ReviewStatus,
    ValidationSeverity,
    WorkflowRunStatus,
)
from ..privacy import (
    JsonScalar,
    bounded_string,
    confidence,
    enum_value,
    json_value,
    non_negative_count,
    optional_string,
    stable_id,
    utc_timestamp,
    validate_safe_metadata,
)


_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CHECKSUM = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def _contract_value(value: Any) -> Any:
    if isinstance(value, WriterContract):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_contract_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _contract_value(item) for key, item in value.items()}
    return json_value(value)


def _metadata(command: Any) -> None:
    object.__setattr__(command, "metadata", validate_safe_metadata(command.metadata))


def _expected_version(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("expected_version must be a positive integer or null")
    return value


class WriterContract:
    def to_dict(self) -> dict[str, Any]:
        return {item.name: _contract_value(getattr(self, item.name)) for item in fields(self)}


@dataclass(frozen=True, slots=True)
class ArtifactReference(WriterContract):
    artifact_id: str
    artifact_kind: str
    producer: str
    checksum: str | None = None

    def __post_init__(self) -> None:
        for name in ("artifact_id", "artifact_kind", "producer"):
            value = bounded_string(getattr(self, name), name, maximum=128)
            if not _OPAQUE_ID.fullmatch(value):
                raise ValueError(f"{name} must be an opaque bounded identifier")
            object.__setattr__(self, name, value)
        checksum = optional_string(self.checksum, "checksum", maximum=128)
        if checksum is not None:
            checksum = checksum.lower()
            if not _CHECKSUM.fullmatch(checksum):
                raise ValueError("checksum must be a SHA-256 digest")
        object.__setattr__(self, "checksum", checksum)


@dataclass(frozen=True, slots=True)
class ValidationIssueInput(WriterContract):
    issue_id: str
    severity: ValidationSeverity | str
    field: str
    rule_id: str
    code: str
    message: str
    occurred_at: str
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "issue_id", stable_id(self.issue_id, "issue_id"))
        object.__setattr__(self, "severity", enum_value(self.severity, ValidationSeverity, "severity"))
        for name in ("field", "rule_id", "code"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name, maximum=128))
        object.__setattr__(self, "message", bounded_string(self.message, "message"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        _metadata(self)


@dataclass(frozen=True, slots=True)
class MatchingSummaryInput(WriterContract):
    match_id: str
    entity_type: str
    candidate_id: str
    confidence: float
    status: MatchingStatus | str
    occurred_at: str
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for name in ("match_id", "candidate_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "entity_type", bounded_string(self.entity_type, "entity_type", maximum=128))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        object.__setattr__(self, "status", enum_value(self.status, MatchingStatus, "status"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        _metadata(self)


@dataclass(frozen=True, slots=True)
class CreateDocumentCommand(WriterContract):
    document_id: str
    source_event_id: str
    filename: str
    document_type: DocumentType | str
    confidence: float
    received_at: str
    created_at: str
    producer: str
    artifact_reference: ArtifactReference | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for name in ("document_id", "source_event_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "filename", bounded_string(self.filename, "filename"))
        object.__setattr__(self, "document_type", enum_value(self.document_type, DocumentType, "document_type"))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        for name in ("received_at", "created_at"):
            object.__setattr__(self, name, utc_timestamp(getattr(self, name), name))
        object.__setattr__(self, "producer", bounded_string(self.producer, "producer", maximum=128))
        if self.artifact_reference is not None and not isinstance(self.artifact_reference, ArtifactReference):
            raise ValueError("artifact_reference must be an ArtifactReference")
        _metadata(self)


@dataclass(frozen=True, slots=True)
class AppendLifecycleEventCommand(WriterContract):
    event_id: str
    source_event_id: str
    document_id: str
    status: DocumentStatus | str
    occurred_at: str
    source_runtime: str
    source_stage: str
    reason_code: str | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for name in ("event_id", "source_event_id", "document_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "status", enum_value(self.status, DocumentStatus, "status"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        for name in ("source_runtime", "source_stage"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name, maximum=128))
        object.__setattr__(self, "reason_code", optional_string(self.reason_code, "reason_code", maximum=128))
        _metadata(self)


@dataclass(frozen=True, slots=True)
class WriteProcessingSnapshotCommand(WriterContract):
    snapshot_id: str
    source_event_id: str
    document_id: str
    workflow_run_id: str
    stage: str
    status: ProcessingState | str
    started_at: str
    updated_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    expected_version: int | None = None
    artifact_reference: ArtifactReference | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for name in ("snapshot_id", "source_event_id", "document_id", "workflow_run_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "stage", bounded_string(self.stage, "stage", maximum=128))
        object.__setattr__(self, "status", enum_value(self.status, ProcessingState, "status"))
        for name in ("started_at", "updated_at"):
            object.__setattr__(self, name, utc_timestamp(getattr(self, name), name))
        object.__setattr__(self, "completed_at", utc_timestamp(self.completed_at, "completed_at", optional=True))
        if self.duration_ms is not None:
            object.__setattr__(self, "duration_ms", non_negative_count(self.duration_ms, "duration_ms"))
        object.__setattr__(self, "expected_version", _expected_version(self.expected_version))
        if self.artifact_reference is not None and not isinstance(self.artifact_reference, ArtifactReference):
            raise ValueError("artifact_reference must be an ArtifactReference")
        _metadata(self)


@dataclass(frozen=True, slots=True)
class WriteValidationIssuesCommand(WriterContract):
    source_event_id: str
    document_id: str
    validation_run_id: str
    issues: tuple[ValidationIssueInput, ...]

    def __post_init__(self) -> None:
        for name in ("source_event_id", "document_id", "validation_run_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        issues = tuple(self.issues)
        if any(not isinstance(item, ValidationIssueInput) for item in issues):
            raise ValueError("issues must contain ValidationIssueInput values")
        if len({item.issue_id for item in issues}) != len(issues):
            raise ValueError("issue IDs must be unique")
        object.__setattr__(self, "issues", tuple(sorted(issues, key=lambda item: (item.field, item.rule_id, item.issue_id))))


@dataclass(frozen=True, slots=True)
class WriteMatchingSummariesCommand(WriterContract):
    source_event_id: str
    document_id: str
    matching_run_id: str
    summaries: tuple[MatchingSummaryInput, ...]

    def __post_init__(self) -> None:
        for name in ("source_event_id", "document_id", "matching_run_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        summaries = tuple(self.summaries)
        if any(not isinstance(item, MatchingSummaryInput) for item in summaries):
            raise ValueError("summaries must contain MatchingSummaryInput values")
        if len({item.match_id for item in summaries}) != len(summaries):
            raise ValueError("match IDs must be unique")
        object.__setattr__(self, "summaries", tuple(sorted(summaries, key=lambda item: (-item.confidence, item.candidate_id, item.match_id))))


@dataclass(frozen=True, slots=True)
class WriteReviewSummaryCommand(WriterContract):
    source_event_id: str
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
    expected_version: int | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for name in ("source_event_id", "review_case_id", "document_id"):
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
        object.__setattr__(self, "expected_version", _expected_version(self.expected_version))
        _metadata(self)


@dataclass(frozen=True, slots=True)
class WriteCorrectionSummaryCommand(WriterContract):
    source_event_id: str
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

    def __post_init__(self) -> None:
        for name in ("source_event_id", "correction_id", "review_case_id", "document_id", "actor_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        for name in ("field_path", "operation", "reason_code", "source_stage"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name, maximum=128))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        _metadata(self)


@dataclass(frozen=True, slots=True)
class WriteReprocessPlanCommand(WriterContract):
    source_event_id: str
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

    def __post_init__(self) -> None:
        for name in ("source_event_id", "plan_id", "review_case_id", "document_id", "requested_by"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        for name in ("requested_from_stage", "requested_target_stage", "reason_code", "mode"):
            object.__setattr__(self, name, bounded_string(getattr(self, name), name, maximum=128))
        for name in ("invalidated_artifact_count", "retained_artifact_count"):
            object.__setattr__(self, name, non_negative_count(getattr(self, name), name))
        object.__setattr__(self, "created_at", utc_timestamp(self.created_at, "created_at"))
        _metadata(self)


@dataclass(frozen=True, slots=True)
class WriteWorkflowRunCommand(WriterContract):
    source_event_id: str
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
    expected_version: int | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for name in ("source_event_id", "run_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
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
        object.__setattr__(self, "expected_version", _expected_version(self.expected_version))
        _metadata(self)


@dataclass(frozen=True, slots=True)
class WriteAuditEventCommand(WriterContract):
    source_event_id: str
    event_id: str
    event_type: str
    actor_id: str
    occurred_at: str
    document_id: str | None = None
    review_case_id: str | None = None
    workflow_run_id: str | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for name in ("source_event_id", "event_id", "actor_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "event_type", bounded_string(self.event_type, "event_type", maximum=128))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        for name in ("document_id", "review_case_id", "workflow_run_id"):
            object.__setattr__(self, name, optional_string(getattr(self, name), name, maximum=128))
        _metadata(self)
