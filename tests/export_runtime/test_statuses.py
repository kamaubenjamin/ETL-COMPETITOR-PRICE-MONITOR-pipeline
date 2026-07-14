from src.export_runtime import (
    EXPORT_OPERATION_STATUS_VALUES,
    EXPORT_READINESS_ISSUE_CODES,
    EXPORT_STATUS_VALUES,
    ExportOperationStatus,
    ExportReadinessIssueCode,
    ExportStatus,
    ExportTargetType,
)


EXPECTED_STATUSES = (
    "not_ready",
    "ready",
    "preparing",
    "queued",
    "exporting",
    "exported",
    "failed",
    "cancelled",
    "duplicate_prevented",
)


def test_status_catalogs_are_fixed_and_aligned():
    assert EXPORT_STATUS_VALUES == EXPECTED_STATUSES
    assert EXPORT_OPERATION_STATUS_VALUES == EXPECTED_STATUSES
    assert tuple(item.value for item in ExportStatus) == EXPECTED_STATUSES
    assert tuple(item.value for item in ExportOperationStatus) == EXPECTED_STATUSES


def test_readiness_issue_codes_are_fixed():
    assert EXPORT_READINESS_ISSUE_CODES == (
        "document_not_found",
        "tenant_scope_denied",
        "permission_denied",
        "invalid_lifecycle_state",
        "validation_not_passed",
        "matching_not_completed",
        "review_not_approved",
        "required_entities_missing",
        "export_target_missing",
        "duplicate_export_active",
        "payload_invalid",
        "adapter_unavailable",
        "internal_error",
    )
    assert ExportReadinessIssueCode.PERMISSION_DENIED.value == "permission_denied"


def test_target_types_are_deterministic():
    assert tuple(item.value for item in ExportTargetType) == ("erp", "csv", "file")

