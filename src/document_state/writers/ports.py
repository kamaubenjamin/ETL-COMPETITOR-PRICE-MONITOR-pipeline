"""Read-write intent ports for internal Document State writer services."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .commands import (
    AppendLifecycleEventCommand,
    CreateDocumentCommand,
    WriteAuditEventCommand,
    WriteCorrectionSummaryCommand,
    WriteMatchingSummariesCommand,
    WriteProcessingSnapshotCommand,
    WriteReprocessPlanCommand,
    WriteReviewSummaryCommand,
    WriteValidationIssuesCommand,
    WriteWorkflowRunCommand,
)
from .results import WriterResult


@runtime_checkable
class IngestionDocumentStateWriterPort(Protocol):
    def create_document(self, command: CreateDocumentCommand) -> WriterResult: ...
    def append_lifecycle_event(self, command: AppendLifecycleEventCommand) -> WriterResult: ...


@runtime_checkable
class ProcessingDocumentStateWriterPort(Protocol):
    def write_processing_snapshot(self, command: WriteProcessingSnapshotCommand) -> WriterResult: ...
    def write_validation_issues(self, command: WriteValidationIssuesCommand) -> WriterResult: ...
    def write_matching_summaries(self, command: WriteMatchingSummariesCommand) -> WriterResult: ...


@runtime_checkable
class ReviewDocumentStateWriterPort(Protocol):
    def write_review_summary(self, command: WriteReviewSummaryCommand) -> WriterResult: ...
    def write_correction_summary(self, command: WriteCorrectionSummaryCommand) -> WriterResult: ...
    def write_reprocess_plan(self, command: WriteReprocessPlanCommand) -> WriterResult: ...


@runtime_checkable
class WorkflowDocumentStateWriterPort(Protocol):
    def write_workflow_run(self, command: WriteWorkflowRunCommand) -> WriterResult: ...


@runtime_checkable
class AuditDocumentStateWriterPort(Protocol):
    def write_audit_event(self, command: WriteAuditEventCommand) -> WriterResult: ...


@runtime_checkable
class DocumentStateWriterPort(
    IngestionDocumentStateWriterPort,
    ProcessingDocumentStateWriterPort,
    ReviewDocumentStateWriterPort,
    WorkflowDocumentStateWriterPort,
    AuditDocumentStateWriterPort,
    Protocol,
):
    pass
