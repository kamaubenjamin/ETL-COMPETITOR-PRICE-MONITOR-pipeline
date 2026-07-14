"""Safe processing and writer intent contracts for upload activation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import (
    UploadArtifactReference,
    UploadContract,
    optional_text,
    optional_timestamp,
    safe_code,
    stable_id,
)


class UploadProcessingStatus(str, Enum):
    INGESTION_REQUESTED = "ingestion_requested"
    PROCESSING_STARTED = "processing_started"
    FAILED = "failed"
    DEFERRED_STAGING_REQUIRED = "deferred_staging_required"
    UNSUPPORTED_ACTIVATION = "unsupported_activation"
    DOCUMENT_STATE_RECORDED = "document_state_recorded"


@dataclass(frozen=True, slots=True)
class UploadIngestionActivationIntent(UploadContract):
    upload_id: str
    document_id: str
    tenant_id: str
    actor_id: str
    source: str
    file_type: str
    artifact_reference: UploadArtifactReference
    requested_at: str | None = None

    def __post_init__(self) -> None:
        for name in ("upload_id", "document_id", "tenant_id", "actor_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "source", safe_code(self.source, "source"))
        object.__setattr__(self, "file_type", safe_code(self.file_type, "file_type"))
        if not isinstance(self.artifact_reference, UploadArtifactReference):
            raise ValueError("artifact_reference is invalid")
        object.__setattr__(self, "requested_at", optional_timestamp(self.requested_at, "requested_at"))


@dataclass(frozen=True, slots=True)
class UploadDocumentStateWriteIntent(UploadContract):
    upload_id: str
    document_id: str
    tenant_id: str
    actor_id: str
    source_event_id: str
    filename: str
    document_type_hint: str | None
    received_at: str
    artifact_reference_id: str
    lifecycle_status: str = "received"

    def __post_init__(self) -> None:
        for name in ("upload_id", "document_id", "tenant_id", "actor_id", "source_event_id", "artifact_reference_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        object.__setattr__(self, "filename", optional_text(self.filename, "filename"))
        object.__setattr__(self, "document_type_hint", optional_text(self.document_type_hint, "document_type_hint", maximum=64))
        timestamp = optional_timestamp(self.received_at, "received_at")
        if timestamp is None:
            raise ValueError("received_at is required")
        object.__setattr__(self, "received_at", timestamp)
        if self.lifecycle_status != "received":
            raise ValueError("lifecycle_status must be received")


@dataclass(frozen=True, slots=True)
class UploadActivationResult(UploadContract):
    upload_id: str | None
    document_id: str | None
    status: UploadProcessingStatus | str
    reason_code: str
    lifecycle_stage: str | None = None
    document_state_recorded: bool = False

    def __post_init__(self) -> None:
        if self.upload_id is not None:
            object.__setattr__(self, "upload_id", stable_id(self.upload_id, "upload_id"))
        if self.document_id is not None:
            object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        try:
            status = self.status if isinstance(self.status, UploadProcessingStatus) else UploadProcessingStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("processing status is invalid") from None
        object.__setattr__(self, "status", status.value)
        object.__setattr__(self, "reason_code", safe_code(self.reason_code, "reason_code"))
        object.__setattr__(self, "lifecycle_stage", optional_text(self.lifecycle_stage, "lifecycle_stage", maximum=64))
        if not isinstance(self.document_state_recorded, bool):
            raise ValueError("document_state_recorded must be a boolean")
        if status == UploadProcessingStatus.INGESTION_REQUESTED and not self.document_state_recorded:
            raise ValueError("ingestion request requires recorded document state")

