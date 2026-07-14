"""Stable service statuses and privacy-safe messages."""

from __future__ import annotations

from enum import Enum


class ExportServiceStatus(str, Enum):
    EXPORTED = "exported"
    FAILED = "failed"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    BLOCKED_NOT_READY = "blocked_not_ready"
    DUPLICATE_PREVENTED = "duplicate_prevented"
    INVALID_COMMAND = "invalid_command"
    INVALID_PAYLOAD = "invalid_payload"
    REPOSITORY_ERROR = "repository_error"


_SAFE_MESSAGES = {
    ExportServiceStatus.EXPORTED: "Export completed successfully.",
    ExportServiceStatus.FAILED: "Export did not complete successfully.",
    ExportServiceStatus.ADAPTER_UNAVAILABLE: "Export adapter is unavailable.",
    ExportServiceStatus.BLOCKED_NOT_READY: "Document is not ready for export.",
    ExportServiceStatus.DUPLICATE_PREVENTED: "An equivalent or conflicting export is already active.",
    ExportServiceStatus.INVALID_COMMAND: "Export command is invalid.",
    ExportServiceStatus.INVALID_PAYLOAD: "Export payload could not be prepared safely.",
    ExportServiceStatus.REPOSITORY_ERROR: "Export repository operation could not be completed.",
}


def export_service_message(status: ExportServiceStatus | str) -> str:
    try:
        resolved = status if isinstance(status, ExportServiceStatus) else ExportServiceStatus(status)
    except (TypeError, ValueError):
        raise ValueError("service status is invalid") from None
    return _SAFE_MESSAGES[resolved]
