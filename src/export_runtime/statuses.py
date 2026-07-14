"""Fixed v1 export runtime status catalogs."""

from __future__ import annotations

from enum import Enum


class ExportStatus(str, Enum):
    NOT_READY = "not_ready"
    READY = "ready"
    PREPARING = "preparing"
    QUEUED = "queued"
    EXPORTING = "exporting"
    EXPORTED = "exported"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DUPLICATE_PREVENTED = "duplicate_prevented"


class ExportOperationStatus(str, Enum):
    """Attempt-level status vocabulary, intentionally aligned with ExportStatus v1."""

    NOT_READY = "not_ready"
    READY = "ready"
    PREPARING = "preparing"
    QUEUED = "queued"
    EXPORTING = "exporting"
    EXPORTED = "exported"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DUPLICATE_PREVENTED = "duplicate_prevented"


class ExportOperationType(str, Enum):
    PREPARE = "prepare"
    EXPORT = "export"
    RETRY = "retry"


class ExportTargetType(str, Enum):
    ERP = "erp"
    CSV = "csv"
    FILE = "file"


class ExportReadinessIssueCode(str, Enum):
    DOCUMENT_NOT_FOUND = "document_not_found"
    TENANT_SCOPE_DENIED = "tenant_scope_denied"
    PERMISSION_DENIED = "permission_denied"
    INVALID_LIFECYCLE_STATE = "invalid_lifecycle_state"
    VALIDATION_NOT_PASSED = "validation_not_passed"
    MATCHING_NOT_COMPLETED = "matching_not_completed"
    REVIEW_NOT_APPROVED = "review_not_approved"
    REQUIRED_ENTITIES_MISSING = "required_entities_missing"
    EXPORT_TARGET_MISSING = "export_target_missing"
    DUPLICATE_EXPORT_ACTIVE = "duplicate_export_active"
    PAYLOAD_INVALID = "payload_invalid"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    INTERNAL_ERROR = "internal_error"


EXPORT_STATUS_VALUES = tuple(item.value for item in ExportStatus)
EXPORT_OPERATION_STATUS_VALUES = tuple(item.value for item in ExportOperationStatus)
EXPORT_READINESS_ISSUE_CODES = tuple(item.value for item in ExportReadinessIssueCode)

