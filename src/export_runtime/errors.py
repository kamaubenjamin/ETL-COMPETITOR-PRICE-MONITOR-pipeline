"""Stable privacy-safe export runtime errors."""

from __future__ import annotations

from enum import Enum

from .contracts import safe_code


class ExportErrorCode(str, Enum):
    INVALID_CONTRACT = "invalid_contract"
    INVALID_STATUS = "invalid_status"
    INVALID_PAYLOAD = "invalid_payload"
    PRIVACY_REJECTED = "privacy_rejected"
    NOT_READY = "not_ready"
    DOCUMENT_NOT_FOUND = "document_not_found"
    TENANT_SCOPE_DENIED = "tenant_scope_denied"
    PERMISSION_DENIED = "permission_denied"
    DUPLICATE_EXPORT = "duplicate_export"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    ADAPTER_FAILED = "adapter_failed"
    LIFECYCLE_CONFLICT = "lifecycle_conflict"
    INTERNAL_ERROR = "internal_error"


_SAFE_MESSAGES = {
    ExportErrorCode.INVALID_CONTRACT: "Export contract is invalid.",
    ExportErrorCode.INVALID_STATUS: "Export status is invalid.",
    ExportErrorCode.INVALID_PAYLOAD: "Export payload is invalid.",
    ExportErrorCode.PRIVACY_REJECTED: "Export payload violates privacy requirements.",
    ExportErrorCode.NOT_READY: "Document is not ready for export.",
    ExportErrorCode.DOCUMENT_NOT_FOUND: "Document is unavailable for export.",
    ExportErrorCode.TENANT_SCOPE_DENIED: "Export scope is not permitted.",
    ExportErrorCode.PERMISSION_DENIED: "Export permission is required.",
    ExportErrorCode.DUPLICATE_EXPORT: "An equivalent export already exists.",
    ExportErrorCode.ADAPTER_UNAVAILABLE: "Export adapter is unavailable.",
    ExportErrorCode.ADAPTER_FAILED: "Export adapter did not confirm success.",
    ExportErrorCode.LIFECYCLE_CONFLICT: "Export lifecycle update is pending.",
    ExportErrorCode.INTERNAL_ERROR: "Export operation could not be completed.",
}


class ExportError(Exception):
    def __init__(
        self,
        code: ExportErrorCode | str,
        *,
        field: str | None = None,
        message: str | None = None,
    ) -> None:
        try:
            resolved_code = code if isinstance(code, ExportErrorCode) else ExportErrorCode(code)
        except (TypeError, ValueError):
            raise ValueError("unsupported export error code") from None
        self.code = resolved_code.value
        self.field = None if field is None else safe_code(field, "field")
        self.message = _SAFE_MESSAGES[resolved_code]
        self.detail_was_sanitized = message is not None
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "detail_was_sanitized": self.detail_was_sanitized,
        }
