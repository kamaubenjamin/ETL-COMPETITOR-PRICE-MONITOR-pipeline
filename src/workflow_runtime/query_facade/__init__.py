"""Public contracts for the Workflow Query Facade."""

from .contracts import (
    AuditEventQuery,
    AuditEventType,
    DocumentQuery,
    DocumentStatus,
    DocumentType,
    OrderingSpec,
    Priority,
    ReviewCaseQuery,
    ReviewStatus,
    SortDirection,
    WorkflowRunQuery,
    WorkflowStatus,
)
from .errors import QueryErrorCode, QueryFacadeError
from .pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PageRequest, PageResult
from .ports import WorkflowQueryFacadePort
from .providers import InMemoryWorkflowQueryFacade
from .read_models import (
    AuditEventSummary,
    CorrectionHistorySummary,
    DocumentDetail,
    DocumentInboxItem,
    MatchingResult,
    ProcessingStatus,
    ReprocessPlanSummary,
    ReviewCaseSummary,
    ValidationIssue,
    WorkflowRunSummary,
)

__all__ = [
    "AuditEventQuery", "AuditEventSummary", "AuditEventType",
    "CorrectionHistorySummary", "DEFAULT_PAGE_LIMIT", "DocumentDetail",
    "DocumentInboxItem", "DocumentQuery", "DocumentStatus", "DocumentType",
    "InMemoryWorkflowQueryFacade", "MAX_PAGE_LIMIT", "MatchingResult", "OrderingSpec", "PageRequest",
    "PageResult", "Priority", "ProcessingStatus", "QueryErrorCode",
    "QueryFacadeError", "ReprocessPlanSummary", "ReviewCaseQuery",
    "ReviewCaseSummary", "ReviewStatus", "SortDirection", "ValidationIssue",
    "WorkflowQueryFacadePort", "WorkflowRunQuery", "WorkflowRunSummary",
    "WorkflowStatus",
]
