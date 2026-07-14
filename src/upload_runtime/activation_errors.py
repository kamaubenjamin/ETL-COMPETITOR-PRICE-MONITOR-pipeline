"""Fixed safe activation reason and error catalog."""

from enum import Enum


class UploadActivationReason(str, Enum):
    VALIDATION_REQUIRED = "validation_required"
    STAGING_REQUIRED = "staging_required"
    ARTIFACT_MISMATCH = "artifact_mismatch"
    DOCUMENT_STATE_REJECTED = "document_state_rejected"
    INGESTION_REJECTED = "ingestion_rejected"
    ACTIVATION_FAILED = "activation_failed"
    INGESTION_ACCEPTED = "ingestion_accepted"

