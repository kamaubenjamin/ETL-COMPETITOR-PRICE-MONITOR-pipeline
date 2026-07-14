"""Safe upload operation result contract."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import UploadArtifactReference, UploadContract, UploadProcessingIntent, UploadStatus, optional_id, safe_code
from .validation import UploadValidationIssue


@dataclass(frozen=True, slots=True)
class UploadResult(UploadContract):
    status: UploadStatus | str
    upload_id: str | None = None
    error_code: str | None = None
    issues: tuple[UploadValidationIssue, ...] = ()
    artifact_reference: UploadArtifactReference | None = None
    processing_intent: UploadProcessingIntent | None = None

    def __post_init__(self) -> None:
        try:
            status = self.status if isinstance(self.status, UploadStatus) else UploadStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("upload result status is invalid") from None
        object.__setattr__(self, "status", status.value)
        object.__setattr__(self, "upload_id", optional_id(self.upload_id, "upload_id"))
        object.__setattr__(self, "error_code", None if self.error_code is None else safe_code(self.error_code, "error_code"))
        issues = tuple(self.issues)
        if any(not isinstance(item, UploadValidationIssue) for item in issues):
            raise ValueError("issues must contain UploadValidationIssue values")
        object.__setattr__(self, "issues", issues)
        if self.artifact_reference is not None and not isinstance(self.artifact_reference, UploadArtifactReference):
            raise ValueError("artifact_reference is invalid")
        if self.processing_intent is not None and not isinstance(self.processing_intent, UploadProcessingIntent):
            raise ValueError("processing_intent is invalid")
        failure = status in {UploadStatus.VALIDATION_FAILED, UploadStatus.FAILED, UploadStatus.DUPLICATE_PREVENTED}
        if failure != (self.error_code is not None):
            raise ValueError("upload result error consistency is invalid")
        if status == UploadStatus.VALIDATION_FAILED and not issues:
            raise ValueError("validation failure requires issues")
        if status == UploadStatus.STAGED and self.artifact_reference is None:
            raise ValueError("staged result requires artifact reference")
        if status == UploadStatus.INGESTION_REQUESTED and self.processing_intent is None:
            raise ValueError("ingestion request requires processing intent")

    @property
    def succeeded(self) -> bool:
        return self.status not in {"validation_failed", "failed", "duplicate_prevented"}

