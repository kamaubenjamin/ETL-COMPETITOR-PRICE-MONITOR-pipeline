"""Public contracts for the isolated upload runtime foundation."""

from .commands import UploadCommand
from .activation import UploadActivationService
from .activation_errors import UploadActivationReason
from .contracts import UploadArtifactReference, UploadFileType, UploadProcessingIntent, UploadSource, UploadStatus
from .errors import UploadError, UploadErrorCode
from .idempotency import UploadIdempotencyKey, upload_idempotency_key
from .ports import UploadArtifactStagingPort
from .integration import (
    DocumentStateWriteReceipt,
    IngestionActivationReceipt,
    UploadDocumentStateWriterPort,
    UploadIngestionActivationPort,
)
from .processing import (
    UploadActivationResult,
    UploadDocumentStateWriteIntent,
    UploadIngestionActivationIntent,
    UploadProcessingStatus,
)
from .progress import STAGE_ORDER, UploadProgressStage, UploadProgressStatus, approximate_progress, stage_sequence
from .progress_errors import UploadProgressErrorCode
from .projections import (
    project_activation_result,
    project_progress_summary,
    project_safe_upload_summary,
    project_timeline,
    project_upload_result,
)
from .queries import UploadProgressQueryService, UploadProgressRecord
from .read_models import (
    UploadDocumentLink,
    UploadProcessingFailure,
    UploadProcessingTimeline,
    UploadProgressEvent,
    UploadProgressPage,
    UploadProgressSummary,
)
from .results import UploadResult
from .validation import UploadValidationIssue, UploadValidationPolicy, UploadValidationResult, validate_upload

__all__ = [
    "DocumentStateWriteReceipt", "IngestionActivationReceipt", "UploadActivationReason",
    "UploadActivationResult", "UploadActivationService", "UploadArtifactReference",
    "UploadArtifactStagingPort", "UploadCommand", "UploadDocumentStateWriteIntent",
    "UploadDocumentStateWriterPort", "UploadIngestionActivationIntent", "UploadIngestionActivationPort", "UploadProcessingStatus", "UploadError",
    "UploadErrorCode", "UploadFileType", "UploadIdempotencyKey", "UploadProcessingIntent",
    "UploadResult", "UploadSource", "UploadStatus", "UploadValidationIssue",
    "UploadValidationPolicy", "UploadValidationResult", "upload_idempotency_key", "validate_upload",
    "STAGE_ORDER", "UploadDocumentLink", "UploadProcessingFailure", "UploadProcessingTimeline",
    "UploadProgressErrorCode", "UploadProgressEvent", "UploadProgressPage", "UploadProgressQueryService",
    "UploadProgressRecord", "UploadProgressStage", "UploadProgressStatus", "UploadProgressSummary", "approximate_progress",
    "project_activation_result", "project_progress_summary", "project_safe_upload_summary",
    "project_timeline", "project_upload_result", "stage_sequence",
]
