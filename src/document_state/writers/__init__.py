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
from .ingestion_writer import IngestionDocumentStateWriter
from .mappings import WRITER_MAPPING_CATALOG, WriterMappingDefinition, WriterMappingEvent, get_writer_mapping
from .ports import (
    AuditDocumentStateWriterPort,
    DocumentStateWriterPort,
    IngestionDocumentStateWriterPort,
    ProcessingDocumentStateWriterPort,
    ReviewDocumentStateWriterPort,
    WorkflowDocumentStateWriterPort,
)
from .processing_writer import ProcessingDocumentStateWriter
from .review_writer import ReviewDocumentStateWriter
from .results import WriterResult, WriterResultStatus
from .workflow_writer import WorkflowDocumentStateWriter

__all__ = [
    "AppendLifecycleEventCommand",
    "ArtifactReference",
    "AuditDocumentStateWriterPort",
    "CreateDocumentCommand",
    "DocumentStateWriterError",
    "DocumentStateWriterPort",
    "IdempotencyDomain",
    "IngestionDocumentStateWriterPort",
    "IngestionDocumentStateWriter",
    "MatchingSummaryInput",
    "ProcessingDocumentStateWriterPort",
    "ProcessingDocumentStateWriter",
    "ReviewDocumentStateWriterPort",
    "ReviewDocumentStateWriter",
    "ValidationIssueInput",
    "WorkflowDocumentStateWriterPort",
    "WorkflowDocumentStateWriter",
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
