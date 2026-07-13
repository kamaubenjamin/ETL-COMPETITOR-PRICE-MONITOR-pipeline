"""Read and write repository interfaces for persistent Document State."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import (
    AuditQuery,
    DocumentQuery,
    LifecycleQuery,
    MatchingQuery,
    ProcessingQuery,
    ReviewQuery,
    ValidationQuery,
    WorkflowRunQuery,
)
from .pagination import PageRequest, PageResult
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


@runtime_checkable
class DocumentReadRepository(Protocol):
    def get_document(self, document_id: str, *, tenant_id: str | None = None) -> DocumentRecord: ...
    def list_documents(self, query: DocumentQuery, page: PageRequest) -> PageResult[DocumentRecord]: ...


@runtime_checkable
class LifecycleReadRepository(Protocol):
    def list_lifecycle_events(self, document_id: str, query: LifecycleQuery, page: PageRequest) -> PageResult[DocumentLifecycleEvent]: ...


@runtime_checkable
class ProcessingReadRepository(Protocol):
    def get_processing_snapshot(self, snapshot_id: str) -> ProcessingSnapshot: ...
    def list_processing_snapshots(self, document_id: str, query: ProcessingQuery, page: PageRequest) -> PageResult[ProcessingSnapshot]: ...


@runtime_checkable
class ValidationReadRepository(Protocol):
    def get_validation_issue(self, issue_id: str) -> ValidationIssueRecord: ...
    def list_validation_issues(self, document_id: str, query: ValidationQuery, page: PageRequest) -> PageResult[ValidationIssueRecord]: ...


@runtime_checkable
class MatchingReadRepository(Protocol):
    def get_matching_summary(self, match_id: str) -> MatchingSummaryRecord: ...
    def list_matching_summaries(self, document_id: str, query: MatchingQuery, page: PageRequest) -> PageResult[MatchingSummaryRecord]: ...


@runtime_checkable
class ReviewReadRepository(Protocol):
    def get_review_reference(self, review_case_id: str) -> ReviewReferenceRecord: ...
    def list_review_references(self, query: ReviewQuery, page: PageRequest) -> PageResult[ReviewReferenceRecord]: ...


@runtime_checkable
class CorrectionReadRepository(Protocol):
    def get_correction_summary(self, correction_id: str) -> CorrectionSummaryRecord: ...
    def list_correction_summaries(self, review_case_id: str, page: PageRequest) -> PageResult[CorrectionSummaryRecord]: ...


@runtime_checkable
class ReprocessReadRepository(Protocol):
    def get_reprocess_plan(self, plan_id: str) -> ReprocessPlanRecord: ...
    def list_reprocess_plans(self, review_case_id: str | None, page: PageRequest) -> PageResult[ReprocessPlanRecord]: ...


@runtime_checkable
class WorkflowRunReadRepository(Protocol):
    def get_workflow_run(self, run_id: str) -> WorkflowRunRecord: ...
    def list_workflow_runs(self, query: WorkflowRunQuery, page: PageRequest) -> PageResult[WorkflowRunRecord]: ...


@runtime_checkable
class AuditReadRepository(Protocol):
    def get_audit_event(self, event_id: str) -> AuditEventRecord: ...
    def list_audit_events(self, query: AuditQuery, page: PageRequest) -> PageResult[AuditEventRecord]: ...


@runtime_checkable
class DocumentStateReadRepositories(
    DocumentReadRepository,
    LifecycleReadRepository,
    ProcessingReadRepository,
    ValidationReadRepository,
    MatchingReadRepository,
    ReviewReadRepository,
    CorrectionReadRepository,
    ReprocessReadRepository,
    WorkflowRunReadRepository,
    AuditReadRepository,
    Protocol,
):
    """Aggregate read surface; intentionally contains no writes."""


@runtime_checkable
class DocumentWriteRepository(Protocol):
    def create_document(self, record: DocumentRecord) -> DocumentRecord: ...
    def update_document(self, record: DocumentRecord, *, expected_version: int) -> DocumentRecord: ...


@runtime_checkable
class LifecycleWriteRepository(Protocol):
    def append_lifecycle_event(self, record: DocumentLifecycleEvent, *, idempotency_key: str) -> DocumentLifecycleEvent: ...


@runtime_checkable
class ProcessingWriteRepository(Protocol):
    def create_processing_snapshot(self, record: ProcessingSnapshot) -> ProcessingSnapshot: ...
    def update_processing_snapshot(self, record: ProcessingSnapshot, *, expected_version: int) -> ProcessingSnapshot: ...


@runtime_checkable
class ValidationWriteRepository(Protocol):
    def append_validation_issue(self, record: ValidationIssueRecord, *, idempotency_key: str) -> ValidationIssueRecord: ...


@runtime_checkable
class MatchingWriteRepository(Protocol):
    def append_matching_summary(self, record: MatchingSummaryRecord, *, idempotency_key: str) -> MatchingSummaryRecord: ...


@runtime_checkable
class ReviewWriteRepository(Protocol):
    def create_review_reference(self, record: ReviewReferenceRecord) -> ReviewReferenceRecord: ...
    def update_review_reference(self, record: ReviewReferenceRecord, *, expected_version: int) -> ReviewReferenceRecord: ...


@runtime_checkable
class CorrectionWriteRepository(Protocol):
    def append_correction_summary(self, record: CorrectionSummaryRecord, *, idempotency_key: str) -> CorrectionSummaryRecord: ...


@runtime_checkable
class ReprocessWriteRepository(Protocol):
    def append_reprocess_plan(self, record: ReprocessPlanRecord, *, idempotency_key: str) -> ReprocessPlanRecord: ...


@runtime_checkable
class WorkflowRunWriteRepository(Protocol):
    def create_workflow_run(self, record: WorkflowRunRecord) -> WorkflowRunRecord: ...
    def update_workflow_run(self, record: WorkflowRunRecord, *, expected_version: int) -> WorkflowRunRecord: ...


@runtime_checkable
class AuditWriteRepository(Protocol):
    def append_audit_event(self, record: AuditEventRecord, *, idempotency_key: str) -> AuditEventRecord: ...


@runtime_checkable
class DocumentStateWriteRepositories(
    DocumentWriteRepository,
    LifecycleWriteRepository,
    ProcessingWriteRepository,
    ValidationWriteRepository,
    MatchingWriteRepository,
    ReviewWriteRepository,
    CorrectionWriteRepository,
    ReprocessWriteRepository,
    WorkflowRunWriteRepository,
    AuditWriteRepository,
    Protocol,
):
    """Aggregate write surface; intentionally contains no reads."""
