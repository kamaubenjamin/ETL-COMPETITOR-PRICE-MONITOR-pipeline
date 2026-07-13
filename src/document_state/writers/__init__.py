"""Public contract surface for internal Document State writers."""

from .commands import (
    AppendLifecycleEventCommand,
    ArtifactReference,
    CreateDocumentCommand,
    MatchingSummaryInput,
    ValidationIssueInput,
    WriteAuditEventCommand,
    WriteCorrectionSummaryCommand,
    WriteMatchingSummariesCommand,
    WriteProcessingSnapshotCommand,
    WriteReprocessPlanCommand,
    WriteReviewSummaryCommand,
    WriteValidationIssuesCommand,
    WriteWorkflowRunCommand,
)
from .errors import DocumentStateWriterError, WriterErrorCode
from .idempotency import IdempotencyDomain, make_idempotency_key
from .mappings import WRITER_MAPPING_CATALOG, WriterMappingDefinition, WriterMappingEvent, get_writer_mapping
from .ports import (
    AuditDocumentStateWriterPort,
    DocumentStateWriterPort,
    IngestionDocumentStateWriterPort,
    ProcessingDocumentStateWriterPort,
    ReviewDocumentStateWriterPort,
    WorkflowDocumentStateWriterPort,
)
from .results import WriterResult, WriterResultStatus

__all__ = [
    "AppendLifecycleEventCommand",
    "ArtifactReference",
    "AuditDocumentStateWriterPort",
    "CreateDocumentCommand",
    "DocumentStateWriterError",
    "DocumentStateWriterPort",
    "IdempotencyDomain",
    "IngestionDocumentStateWriterPort",
    "MatchingSummaryInput",
    "ProcessingDocumentStateWriterPort",
    "ReviewDocumentStateWriterPort",
    "ValidationIssueInput",
    "WorkflowDocumentStateWriterPort",
    "WRITER_MAPPING_CATALOG",
    "WriteAuditEventCommand",
    "WriteCorrectionSummaryCommand",
    "WriteMatchingSummariesCommand",
    "WriteProcessingSnapshotCommand",
    "WriteReprocessPlanCommand",
    "WriteReviewSummaryCommand",
    "WriteValidationIssuesCommand",
    "WriteWorkflowRunCommand",
    "WriterErrorCode",
    "WriterMappingDefinition",
    "WriterMappingEvent",
    "WriterResult",
    "WriterResultStatus",
    "get_writer_mapping",
    "make_idempotency_key",
]
