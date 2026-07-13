"""Public persistence-neutral contracts for Document State."""

from .composition import DocumentStateComposition, compose_document_state
from .contracts import (
    AuditQuery,
    DETERMINISTIC_ORDERING,
    DocumentQuery,
    DocumentStatus,
    DocumentType,
    LifecycleQuery,
    LEGACY_TENANT_ID,
    MatchingQuery,
    MatchingStatus,
    OrderingSpec,
    Priority,
    ProcessingQuery,
    ProcessingState,
    ReviewQuery,
    ReviewStatus,
    SortDirection,
    ValidationQuery,
    ValidationSeverity,
    WorkflowRunQuery,
    WorkflowRunStatus,
)
from .errors import DocumentStateError, DocumentStateErrorCode
from .pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PageRequest, PageResult
from .records import (
    AuditEventRecord,
    CorrectionSummaryRecord,
    DocumentLifecycleEvent,
    DocumentRecord,
    MatchingSummaryRecord,
    ProcessingSnapshot,
    ReprocessPlanRecord,
    ReviewReferenceRecord,
    ValidationIssueRecord,
    WorkflowRunRecord,
)
from .repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories
from .repositories_in_memory import (
    InMemoryDocumentStateReader,
    InMemoryDocumentStateRepositories,
    InMemoryDocumentStateWriter,
)

__all__ = [
    "AuditEventRecord", "AuditQuery", "CorrectionSummaryRecord", "DEFAULT_PAGE_LIMIT",
    "DETERMINISTIC_ORDERING", "DocumentLifecycleEvent", "DocumentQuery", "DocumentRecord",
    "DocumentStateComposition",
    "DocumentStateError", "DocumentStateErrorCode", "DocumentStateReadRepositories",
    "DocumentStateWriteRepositories", "DocumentStatus", "DocumentType",
    "InMemoryDocumentStateReader", "InMemoryDocumentStateRepositories",
    "InMemoryDocumentStateWriter", "LEGACY_TENANT_ID", "LifecycleQuery",
    "MAX_PAGE_LIMIT", "MatchingQuery", "MatchingStatus", "MatchingSummaryRecord", "OrderingSpec",
    "PageRequest", "PageResult", "Priority", "ProcessingQuery", "ProcessingSnapshot",
    "ProcessingState", "ReprocessPlanRecord", "ReviewQuery", "ReviewReferenceRecord",
    "ReviewStatus", "SortDirection", "ValidationIssueRecord", "ValidationQuery",
    "ValidationSeverity", "WorkflowRunQuery", "WorkflowRunRecord", "WorkflowRunStatus",
    "compose_document_state",
]
