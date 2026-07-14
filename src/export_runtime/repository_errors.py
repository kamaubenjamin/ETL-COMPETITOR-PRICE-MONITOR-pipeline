"""Fixed privacy-safe errors for export repositories."""

from __future__ import annotations

from enum import Enum

from .contracts import safe_code


class ExportRepositoryErrorCode(str, Enum):
    INVALID_RECORD = "invalid_record"
    INVALID_QUERY = "invalid_query"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    DUPLICATE_ATTEMPT = "duplicate_attempt"
    DUPLICATE_IDEMPOTENCY_KEY = "duplicate_idempotency_key"
    MISSING_ATTEMPT = "missing_attempt"
    TERMINAL_RESULT_EXISTS = "terminal_result_exists"
    INVALID_TRANSITION = "invalid_transition"
    VERSION_CONFLICT = "version_conflict"
    SOURCE_UNAVAILABLE = "source_unavailable"
    INTERNAL_ERROR = "internal_error"


_SAFE_MESSAGES = {
    ExportRepositoryErrorCode.INVALID_RECORD: "Export repository record is invalid.",
    ExportRepositoryErrorCode.INVALID_QUERY: "Export repository query is invalid.",
    ExportRepositoryErrorCode.NOT_FOUND: "Export repository record was not found.",
    ExportRepositoryErrorCode.CONFLICT: "Export repository record conflicts with existing state.",
    ExportRepositoryErrorCode.DUPLICATE_ATTEMPT: "Export attempt identifier already exists.",
    ExportRepositoryErrorCode.DUPLICATE_IDEMPOTENCY_KEY: "Equivalent export operation already exists.",
    ExportRepositoryErrorCode.MISSING_ATTEMPT: "Export attempt is unavailable for this result.",
    ExportRepositoryErrorCode.TERMINAL_RESULT_EXISTS: "Export attempt already has a terminal result.",
    ExportRepositoryErrorCode.INVALID_TRANSITION: "Export attempt status transition is invalid.",
    ExportRepositoryErrorCode.VERSION_CONFLICT: "Export attempt version has changed.",
    ExportRepositoryErrorCode.SOURCE_UNAVAILABLE: "Export repository is unavailable.",
    ExportRepositoryErrorCode.INTERNAL_ERROR: "Export repository operation could not be completed.",
}


class ExportRepositoryError(Exception):
    def __init__(self, code: ExportRepositoryErrorCode | str, *, field: str | None = None) -> None:
        try:
            resolved = code if isinstance(code, ExportRepositoryErrorCode) else ExportRepositoryErrorCode(code)
        except (TypeError, ValueError):
            raise ValueError("unsupported export repository error code") from None
        self.code = resolved.value
        self.field = None if field is None else safe_code(field, "field")
        self.message = _SAFE_MESSAGES[resolved]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "field": self.field}
