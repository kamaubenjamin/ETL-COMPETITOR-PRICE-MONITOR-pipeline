"""Deterministic read-only in-memory Workflow Query Facade provider."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from ..contracts import AuditEventQuery, DocumentQuery, ReviewCaseQuery, WorkflowRunQuery
from ..errors import QueryErrorCode, QueryFacadeError
from ..pagination import PageRequest, PageResult, SerializableRecord
from ..read_models import (
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


SNAPSHOT_AT = "2026-07-01T09:00:00+00:00"

_DOCUMENTS = (
    DocumentInboxItem("doc-001", "invoice_001.pdf", "invoice", "validated", 0.98, "validate_data", "2026-07-01T08:00:00+00:00", "tenant-demo"),
    DocumentInboxItem("doc-002", "purchase_order_002.pdf", "purchase_order", "review_required", 0.72, "matching", "2026-07-01T08:05:00+00:00", "tenant-demo"),
    DocumentInboxItem("doc-003", "receipt_003.pdf", "receipt", "export_ready", 0.94, "export", "2026-07-01T08:10:00+00:00", "tenant-alt"),
)

_DOCUMENT_DETAILS = {
    "doc-001": DocumentDetail("doc-001", "invoice_001.pdf", "invoice", "validated", 0.98, "validate_data", "2026-07-01T08:00:00+00:00", "2026-07-01T08:00:04+00:00", "invoice_processing", "tenant-demo"),
    "doc-002": DocumentDetail("doc-002", "purchase_order_002.pdf", "purchase_order", "review_required", 0.72, "matching", "2026-07-01T08:05:00+00:00", "2026-07-01T08:05:05+00:00", "purchase_order_processing", "tenant-demo"),
    "doc-003": DocumentDetail("doc-003", "receipt_003.pdf", "receipt", "export_ready", 0.94, "export", "2026-07-01T08:10:00+00:00", "2026-07-01T08:10:06+00:00", "receipt_processing", "tenant-alt"),
}

_PROCESSING = (
    ProcessingStatus("doc-001", "ingest", "succeeded", "2026-07-01T08:00:01+00:00"),
    ProcessingStatus("doc-001", "validate_data", "succeeded", "2026-07-01T08:00:04+00:00"),
    ProcessingStatus("doc-002", "ingest", "succeeded", "2026-07-01T08:05:01+00:00"),
    ProcessingStatus("doc-002", "matching", "review_required", "2026-07-01T08:05:05+00:00"),
    ProcessingStatus("doc-003", "ingest", "succeeded", "2026-07-01T08:10:01+00:00"),
    ProcessingStatus("doc-003", "export", "ready", "2026-07-01T08:10:06+00:00"),
)

_VALIDATION_ISSUES = (
    ValidationIssue("issue-001", "doc-002", "error", "supplier_id", "required_supplier", "required", "Required field is missing."),
    ValidationIssue("issue-002", "doc-002", "warning", "invoice_total", "review_threshold", "threshold", "Field requires operator confirmation."),
    ValidationIssue("issue-003", "doc-003", "warning", "receipt_date", "date_range", "range", "Field requires operator confirmation."),
)

_MATCHING_RESULTS = (
    MatchingResult("match-001", "doc-001", "supplier", "supplier-100", 0.97, "matched"),
    MatchingResult("match-002", "doc-002", "supplier", "supplier-200", 0.72, "ambiguous"),
    MatchingResult("match-003", "doc-002", "supplier", "supplier-201", 0.68, "candidate"),
)

_REVIEW_CASES = (
    ReviewCaseSummary("review-001", "doc-002", "matching_ambiguity", "high", "in_review", "reviewer-01", 1, None, "not_requested", "2026-07-01T08:06:00+00:00", "2026-07-01T08:08:00+00:00"),
    ReviewCaseSummary("review-002", "doc-003", "validation_warning", "normal", "resolved", "reviewer-02", 0, "approve", "not_requested", "2026-07-01T08:11:00+00:00", "2026-07-01T08:13:00+00:00"),
    ReviewCaseSummary("review-003", "doc-001", "corrected_fields", "urgent", "reprocess_requested", "reviewer-03", 1, "request_reprocess", "planned", "2026-07-01T08:15:00+00:00", "2026-07-01T08:18:00+00:00"),
)

_CORRECTIONS = (
    CorrectionHistorySummary("correction-001", "review-001", "supplier_id", "replace", "operator_verified", "reviewer-01", "2026-07-01T08:08:00+00:00", "matching"),
    CorrectionHistorySummary("correction-002", "review-003", "invoice_total", "replace", "corrected_fields", "reviewer-03", "2026-07-01T08:17:00+00:00", "validate_data"),
)

_REPROCESS_PLANS = (
    ReprocessPlanSummary("plan-001", "review-003", "validate_data", "transform", 1, 2, "corrected_fields", "reviewer-03", "2026-07-01T08:18:00+00:00"),
)

_WORKFLOW_RUNS = (
    WorkflowRunSummary("run-001", "invoice_processing", "succeeded", "2026-07-01T08:00:00+00:00", "2026-07-01T08:00:04+00:00", 4000, 3, 3, 0),
    WorkflowRunSummary("run-002", "purchase_order_processing", "running", "2026-07-01T08:05:00+00:00", None, None, 3, 1, 0),
    WorkflowRunSummary("run-003", "receipt_processing", "failed", "2026-07-01T08:10:00+00:00", "2026-07-01T08:10:06+00:00", 6000, 3, 1, 1),
)

_AUDIT_EVENTS = (
    AuditEventSummary("audit-001", "document_received", "system", "2026-07-01T08:00:00+00:00", "doc-001", metadata={"record_type": "invoice"}),
    AuditEventSummary("audit-002", "validation_completed", "system", "2026-07-01T08:05:04+00:00", "doc-002", metadata={"issue_count": 2}),
    AuditEventSummary("audit-003", "review_case_created", "system", "2026-07-01T08:06:00+00:00", "doc-002", "review-001", {"reason_code": "matching_ambiguity"}),
    AuditEventSummary("audit-004", "review_decision_recorded", "reviewer-02", "2026-07-01T08:13:00+00:00", "doc-003", "review-002", {"decision_code": "approve"}),
    AuditEventSummary("audit-005", "reprocess_plan_created", "reviewer-03", "2026-07-01T08:18:00+00:00", "doc-001", "review-003", {"plan_count": 1, "mode": "dry_run"}),
)


T = TypeVar("T", bound=SerializableRecord)


def _page(records: Sequence[T], page: PageRequest) -> PageResult[T]:
    if not isinstance(page, PageRequest):
        raise QueryFacadeError(QueryErrorCode.INVALID_QUERY, field="page")
    items = tuple(records[page.offset : page.offset + page.limit])
    return PageResult(items, total=len(records), limit=page.limit, offset=page.offset, snapshot_at=SNAPSHOT_AT)


class InMemoryWorkflowQueryFacade:
    """Immutable deterministic facade provider for local and test use."""

    def __init__(self, *, simulate_unavailable: bool = False) -> None:
        if not isinstance(simulate_unavailable, bool):
            raise QueryFacadeError(QueryErrorCode.INVALID_QUERY, field="simulate_unavailable")
        self._simulate_unavailable = simulate_unavailable

    def _available(self) -> None:
        if self._simulate_unavailable:
            raise QueryFacadeError(QueryErrorCode.SOURCE_UNAVAILABLE)

    def _document(self, document_id: str, tenant_id: str | None = None) -> DocumentDetail:
        self._available()
        if not isinstance(document_id, str) or not document_id:
            raise QueryFacadeError(QueryErrorCode.INVALID_QUERY, field="document_id")
        record = _DOCUMENT_DETAILS.get(document_id)
        if record is None:
            raise QueryFacadeError(QueryErrorCode.NOT_FOUND, field="document_id")
        if tenant_id is not None and record.tenant_id != tenant_id:
            raise QueryFacadeError(QueryErrorCode.NOT_FOUND, field="document_id")
        return record

    def _review_case(self, review_case_id: str) -> ReviewCaseSummary:
        self._available()
        if not isinstance(review_case_id, str) or not review_case_id:
            raise QueryFacadeError(QueryErrorCode.INVALID_QUERY, field="review_case_id")
        record = next((item for item in _REVIEW_CASES if item.review_case_id == review_case_id), None)
        if record is None:
            raise QueryFacadeError(QueryErrorCode.NOT_FOUND, field="review_case_id")
        return record

    def list_documents(self, query: DocumentQuery, page: PageRequest) -> PageResult[DocumentInboxItem]:
        self._available()
        if not isinstance(query, DocumentQuery):
            raise QueryFacadeError(QueryErrorCode.INVALID_QUERY, field="query")
        records = tuple(sorted((item for item in _DOCUMENTS if (query.status is None or item.status == query.status) and (query.document_type is None or item.document_type == query.document_type) and (query.tenant_id is None or item.tenant_id == query.tenant_id)), key=lambda item: (item.received_at, item.document_id)))
        return _page(records, page)

    def get_document(self, document_id: str, *, tenant_id: str | None = None) -> DocumentDetail:
        return self._document(document_id, tenant_id)

    def list_processing(self, document_id: str, page: PageRequest) -> PageResult[ProcessingStatus]:
        self._document(document_id)
        records = tuple(sorted((item for item in _PROCESSING if item.document_id == document_id), key=lambda item: (item.occurred_at, item.stage)))
        return _page(records, page)

    def get_processing_status(self, document_id: str, page: PageRequest) -> PageResult[ProcessingStatus]:
        return self.list_processing(document_id, page)

    def list_validation_issues(self, document_id: str, page: PageRequest) -> PageResult[ValidationIssue]:
        self._document(document_id)
        severity = {"error": 0, "warning": 1}
        records = tuple(sorted((item for item in _VALIDATION_ISSUES if item.document_id == document_id), key=lambda item: (severity[item.severity], item.field, item.rule_id, item.issue_id)))
        return _page(records, page)

    def list_matching_results(self, document_id: str, page: PageRequest) -> PageResult[MatchingResult]:
        self._document(document_id)
        records = tuple(sorted((item for item in _MATCHING_RESULTS if item.document_id == document_id), key=lambda item: (-item.confidence, item.candidate_id, item.match_id)))
        return _page(records, page)

    def list_review_cases(self, query: ReviewCaseQuery, page: PageRequest) -> PageResult[ReviewCaseSummary]:
        self._available()
        if not isinstance(query, ReviewCaseQuery):
            raise QueryFacadeError(QueryErrorCode.INVALID_QUERY, field="query")
        records = tuple(sorted((item for item in _REVIEW_CASES if (query.status is None or item.status == query.status) and (query.priority is None or item.priority == query.priority)), key=lambda item: (item.created_at, item.review_case_id)))
        return _page(records, page)

    def get_review_case(self, review_case_id: str) -> ReviewCaseSummary:
        return self._review_case(review_case_id)

    def list_correction_history(self, review_case_id: str, page: PageRequest) -> PageResult[CorrectionHistorySummary]:
        self._review_case(review_case_id)
        records = tuple(sorted((item for item in _CORRECTIONS if item.review_case_id == review_case_id), key=lambda item: (item.occurred_at, item.correction_id)))
        return _page(records, page)

    def list_corrections(self, review_case_id: str, page: PageRequest) -> PageResult[CorrectionHistorySummary]:
        return self.list_correction_history(review_case_id, page)

    def list_reprocess_plans(self, review_case_id: str | None, page: PageRequest) -> PageResult[ReprocessPlanSummary]:
        self._available()
        if review_case_id is not None:
            self._review_case(review_case_id)
        records = tuple(sorted((item for item in _REPROCESS_PLANS if review_case_id is None or item.review_case_id == review_case_id), key=lambda item: (item.created_at, item.plan_id)))
        return _page(records, page)

    def list_workflow_runs(self, query: WorkflowRunQuery, page: PageRequest) -> PageResult[WorkflowRunSummary]:
        self._available()
        if not isinstance(query, WorkflowRunQuery):
            raise QueryFacadeError(QueryErrorCode.INVALID_QUERY, field="query")
        filtered = tuple(item for item in _WORKFLOW_RUNS if (query.status is None or item.status == query.status) and (query.workflow_name is None or item.workflow_name == query.workflow_name))
        records = tuple(sorted(sorted(filtered, key=lambda item: item.run_id), key=lambda item: item.started_at, reverse=True))
        return _page(records, page)

    def list_audit_events(self, query: AuditEventQuery, page: PageRequest) -> PageResult[AuditEventSummary]:
        self._available()
        if not isinstance(query, AuditEventQuery):
            raise QueryFacadeError(QueryErrorCode.INVALID_QUERY, field="query")
        filtered = tuple(item for item in _AUDIT_EVENTS if query.event_type is None or item.event_type == query.event_type)
        records = tuple(sorted(sorted(filtered, key=lambda item: item.event_id), key=lambda item: item.occurred_at, reverse=True))
        return _page(records, page)
