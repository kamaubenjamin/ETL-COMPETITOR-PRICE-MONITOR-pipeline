"""Shared query filters and deterministic ordering contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar


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


class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AuditEventType(str, Enum):
    DOCUMENT_RECEIVED = "document_received"
    VALIDATION_COMPLETED = "validation_completed"
    REVIEW_CASE_CREATED = "review_case_created"
    REVIEW_DECISION_RECORDED = "review_decision_recorded"
    REPROCESS_PLAN_CREATED = "reprocess_plan_created"


class SortDirection(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


E = TypeVar("E", bound=Enum)


def enum_value(value: E | str | None, enum_type: type[E], field_name: str) -> str | None:
    if value is None:
        return None
    try:
        return value.value if isinstance(value, enum_type) else enum_type(value).value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} is invalid") from exc


@dataclass(frozen=True, slots=True)
class OrderingSpec:
    fields: tuple[str, ...]
    directions: tuple[SortDirection | str, ...]

    def __post_init__(self) -> None:
        if not self.fields or len(self.fields) != len(self.directions):
            raise ValueError("ordering fields and directions must be non-empty and aligned")
        if any(not isinstance(field, str) or not field or len(field) > 64 for field in self.fields):
            raise ValueError("ordering fields must be bounded strings")
        object.__setattr__(
            self,
            "directions",
            tuple(SortDirection(direction) for direction in self.directions),
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "fields": list(self.fields),
            "directions": [direction.value for direction in self.directions],
        }


@dataclass(frozen=True, slots=True)
class DocumentQuery:
    status: DocumentStatus | str | None = None
    document_type: DocumentType | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", enum_value(self.status, DocumentStatus, "status"))
        object.__setattr__(self, "document_type", enum_value(self.document_type, DocumentType, "document_type"))

    def to_dict(self) -> dict[str, str | None]:
        return {"status": self.status, "document_type": self.document_type}


@dataclass(frozen=True, slots=True)
class ReviewCaseQuery:
    status: ReviewStatus | str | None = None
    priority: Priority | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", enum_value(self.status, ReviewStatus, "status"))
        object.__setattr__(self, "priority", enum_value(self.priority, Priority, "priority"))

    def to_dict(self) -> dict[str, str | None]:
        return {"status": self.status, "priority": self.priority}


@dataclass(frozen=True, slots=True)
class WorkflowRunQuery:
    status: WorkflowStatus | str | None = None
    workflow_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", enum_value(self.status, WorkflowStatus, "status"))
        if self.workflow_name is not None:
            object.__setattr__(self, "workflow_name", bounded_string(self.workflow_name, "workflow_name"))

    def to_dict(self) -> dict[str, str | None]:
        return {"status": self.status, "workflow_name": self.workflow_name}


@dataclass(frozen=True, slots=True)
class AuditEventQuery:
    event_type: AuditEventType | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", enum_value(self.event_type, AuditEventType, "event_type"))

    def to_dict(self) -> dict[str, str | None]:
        return {"event_type": self.event_type}


def bounded_string(value: Any, field_name: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{field_name} must be a bounded non-empty string")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field_name} contains unsupported characters")
    return value
