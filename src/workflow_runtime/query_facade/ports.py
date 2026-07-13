"""Read-only structural ports for query sources and facade consumers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import AuditEventQuery, DocumentQuery, ReviewCaseQuery, WorkflowRunQuery
from .pagination import PageRequest, PageResult
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


@runtime_checkable
class DocumentReadPort(Protocol):
    def list_documents(self, query: DocumentQuery, page: PageRequest) -> PageResult[DocumentInboxItem]: ...

    def get_document(self, document_id: str, *, tenant_id: str | None = None) -> DocumentDetail: ...


@runtime_checkable
class ProcessingReadPort(Protocol):
    def list_processing(self, document_id: str, page: PageRequest) -> PageResult[ProcessingStatus]: ...


@runtime_checkable
class ValidationReadPort(Protocol):
    def list_validation_issues(self, document_id: str, page: PageRequest) -> PageResult[ValidationIssue]: ...


@runtime_checkable
class MatchingReadPort(Protocol):
    def list_matching_results(self, document_id: str, page: PageRequest) -> PageResult[MatchingResult]: ...


@runtime_checkable
class ReviewReadPort(Protocol):
    def list_review_cases(self, query: ReviewCaseQuery, page: PageRequest) -> PageResult[ReviewCaseSummary]: ...

    def get_review_case(self, review_case_id: str) -> ReviewCaseSummary: ...

    def list_correction_history(self, review_case_id: str, page: PageRequest) -> PageResult[CorrectionHistorySummary]: ...

    def list_reprocess_plans(self, review_case_id: str | None, page: PageRequest) -> PageResult[ReprocessPlanSummary]: ...


@runtime_checkable
class WorkflowRunReadPort(Protocol):
    def list_workflow_runs(self, query: WorkflowRunQuery, page: PageRequest) -> PageResult[WorkflowRunSummary]: ...


@runtime_checkable
class AuditReadPort(Protocol):
    def list_audit_events(self, query: AuditEventQuery, page: PageRequest) -> PageResult[AuditEventSummary]: ...


@runtime_checkable
class WorkflowQueryFacadePort(
    DocumentReadPort,
    ProcessingReadPort,
    ValidationReadPort,
    MatchingReadPort,
    ReviewReadPort,
    WorkflowRunReadPort,
    AuditReadPort,
    Protocol,
):
    """Complete public read surface; intentionally contains no commands."""
