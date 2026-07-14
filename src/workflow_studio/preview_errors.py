"""Fixed non-reflective preview issue codes and messages."""
from enum import Enum

class WorkflowPreviewErrorCode(str, Enum):
    IDENTITY_MISMATCH="identity_mismatch"
    VALIDATION_BLOCKED="validation_blocked"
    PREVIEW_INELIGIBLE="preview_ineligible"
    REQUIRED_FEATURE_UNAVAILABLE="required_feature_unavailable"
    LEGACY_REVIEW_UNRESOLVED="legacy_review_unresolved"
    FIXTURE_INVALID="fixture_invalid"
    FIXTURE_NOT_FOUND="fixture_not_found"
    LIMIT_EXCEEDED="limit_exceeded"
    PREVIEW_UNAVAILABLE="preview_unavailable"
    ADAPTER_FAILED="adapter_failed"
    CANCELLED="cancelled"

PREVIEW_MESSAGES = {
    WorkflowPreviewErrorCode.IDENTITY_MISMATCH:"Preview identity does not match the supplied workflow version.",
    WorkflowPreviewErrorCode.VALIDATION_BLOCKED:"Workflow validation blocks preview execution.",
    WorkflowPreviewErrorCode.PREVIEW_INELIGIBLE:"One or more workflow actions are not eligible for preview.",
    WorkflowPreviewErrorCode.REQUIRED_FEATURE_UNAVAILABLE:"A preview-required feature is unavailable.",
    WorkflowPreviewErrorCode.LEGACY_REVIEW_UNRESOLVED:"Legacy compatibility review blocks preview execution.",
    WorkflowPreviewErrorCode.FIXTURE_INVALID:"Preview fixture is invalid or exceeds privacy bounds.",
    WorkflowPreviewErrorCode.FIXTURE_NOT_FOUND:"Approved preview fixture was not found.",
    WorkflowPreviewErrorCode.LIMIT_EXCEEDED:"Preview exceeded a configured safety limit.",
    WorkflowPreviewErrorCode.PREVIEW_UNAVAILABLE:"Preview execution is unavailable.",
    WorkflowPreviewErrorCode.ADAPTER_FAILED:"Preview execution failed safely.",
    WorkflowPreviewErrorCode.CANCELLED:"Preview execution was cancelled.",
}
