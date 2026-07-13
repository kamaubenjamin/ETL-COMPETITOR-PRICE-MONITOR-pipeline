"""Stable statuses, filters, and ordering contracts for Document State."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from .privacy import bounded_string, enum_value, optional_enum_value, optional_string, stable_id


LEGACY_TENANT_ID = "tenant-local"


class DocumentStatus(str, Enum):
    RECEIVED = "received"
    INGESTED = "ingested"
    CLASSIFIED = "classified"
    PARSED = "parsed"
    EXTRACTED = "extracted"
    TRANSFORMED = "transformed"
    VALIDATED = "validated"
    MATCHED = "matched"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    EXPORT_READY = "export_ready"
    EXPORTED = "exported"
    FAILED = "failed"


class DocumentType(str, Enum):
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    RECEIPT = "receipt"
    BANK_STATEMENT = "bank_statement"


class ProcessingState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ValidationSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class MatchingStatus(str, Enum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"
    REVIEW_REQUIRED = "review_required"


class ReviewStatus(str, Enum):
    REVIEW_REQUIRED = "review_required"
    IN_REVIEW = "in_review"
    CORRECTED = "corrected"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    REPROCESS_REQUESTED = "reprocess_requested"
    RESOLVED = "resolved"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class WorkflowRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SortDirection(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


@dataclass(frozen=True, slots=True)
class OrderingSpec:
    fields: tuple[str, ...]
    directions: tuple[SortDirection | str, ...]

    def __post_init__(self) -> None:
        if not self.fields or len(self.fields) != len(self.directions):
            raise ValueError("ordering fields and directions must be non-empty and aligned")
        object.__setattr__(self, "fields", tuple(bounded_string(item, "ordering field", maximum=64) for item in self.fields))
        object.__setattr__(self, "directions", tuple(SortDirection(item).value for item in self.directions))

    def to_dict(self) -> dict[str, list[str]]:
        return {"fields": list(self.fields), "directions": list(self.directions)}


@dataclass(frozen=True, slots=True)
class DocumentQuery:
    status: DocumentStatus | str | None = None
    document_type: DocumentType | str | None = None
    tenant_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", optional_enum_value(self.status, DocumentStatus, "status"))
        object.__setattr__(self, "document_type", optional_enum_value(self.document_type, DocumentType, "document_type"))
        if self.tenant_id is not None:
            object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))


@dataclass(frozen=True, slots=True)
class LifecycleQuery:
    status: DocumentStatus | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", optional_enum_value(self.status, DocumentStatus, "status"))


@dataclass(frozen=True, slots=True)
class ProcessingQuery:
    status: ProcessingState | str | None = None
    workflow_run_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", optional_enum_value(self.status, ProcessingState, "status"))
        object.__setattr__(self, "workflow_run_id", optional_string(self.workflow_run_id, "workflow_run_id", maximum=128))


@dataclass(frozen=True, slots=True)
class ValidationQuery:
    severity: ValidationSeverity | str | None = None
    rule_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", optional_enum_value(self.severity, ValidationSeverity, "severity"))
        object.__setattr__(self, "rule_id", optional_string(self.rule_id, "rule_id", maximum=128))


@dataclass(frozen=True, slots=True)
class MatchingQuery:
    status: MatchingStatus | str | None = None
    entity_type: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", optional_enum_value(self.status, MatchingStatus, "status"))
        object.__setattr__(self, "entity_type", optional_string(self.entity_type, "entity_type", maximum=128))


@dataclass(frozen=True, slots=True)
class ReviewQuery:
    status: ReviewStatus | str | None = None
    priority: Priority | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", optional_enum_value(self.status, ReviewStatus, "status"))
        object.__setattr__(self, "priority", optional_enum_value(self.priority, Priority, "priority"))


@dataclass(frozen=True, slots=True)
class WorkflowRunQuery:
    status: WorkflowRunStatus | str | None = None
    workflow_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", optional_enum_value(self.status, WorkflowRunStatus, "status"))
        object.__setattr__(self, "workflow_name", optional_string(self.workflow_name, "workflow_name"))


@dataclass(frozen=True, slots=True)
class AuditQuery:
    event_type: str | None = None
    document_id: str | None = None
    review_case_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("event_type", "document_id", "review_case_id"):
            object.__setattr__(self, name, optional_string(getattr(self, name), name, maximum=128))


DETERMINISTIC_ORDERING = MappingProxyType(
    {
        "audit_event": OrderingSpec(("occurred_at", "event_id"), ("desc", "asc")),
        "correction_summary": OrderingSpec(("occurred_at", "correction_id"), ("asc", "asc")),
        "document": OrderingSpec(("received_at", "document_id"), ("asc", "asc")),
        "lifecycle_event": OrderingSpec(("occurred_at", "event_id"), ("asc", "asc")),
        "matching_summary": OrderingSpec(("confidence", "candidate_id", "match_id"), ("desc", "asc", "asc")),
        "processing_snapshot": OrderingSpec(("updated_at", "stage", "snapshot_id"), ("asc", "asc", "asc")),
        "reprocess_plan": OrderingSpec(("created_at", "plan_id"), ("desc", "asc")),
        "review_reference": OrderingSpec(("priority", "created_at", "review_case_id"), ("desc", "asc", "asc")),
        "validation_issue": OrderingSpec(("severity", "field", "rule_id", "issue_id"), ("desc", "asc", "asc", "asc")),
        "workflow_run": OrderingSpec(("started_at", "run_id"), ("desc", "asc")),
    }
)


def query_to_dict(query: Any) -> dict[str, str | None]:
    values = {name: getattr(query, name) for name in query.__dataclass_fields__}
    if isinstance(query, DocumentQuery) and values.get("tenant_id") is None:
        values.pop("tenant_id")
    return values
