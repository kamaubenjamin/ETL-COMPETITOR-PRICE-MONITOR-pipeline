"""Stable privacy-safe errors for Document State repositories."""

from __future__ import annotations

from enum import Enum

from .privacy import optional_string


class DocumentStateErrorCode(str, Enum):
    INVALID_RECORD = "invalid_record"
    INVALID_QUERY = "invalid_query"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    SOURCE_UNAVAILABLE = "source_unavailable"
    INTERNAL_ERROR = "internal_error"


_SAFE_MESSAGES = {
    DocumentStateErrorCode.INVALID_RECORD: "Document state record is invalid.",
    DocumentStateErrorCode.INVALID_QUERY: "Document state query is invalid.",
    DocumentStateErrorCode.NOT_FOUND: "Document state record was not found.",
    DocumentStateErrorCode.CONFLICT: "Document state conflict was detected.",
    DocumentStateErrorCode.SOURCE_UNAVAILABLE: "Document state source is unavailable.",
    DocumentStateErrorCode.INTERNAL_ERROR: "Document state operation could not be completed.",
}


class DocumentStateError(Exception):
    def __init__(self, code: DocumentStateErrorCode | str, *, field: str | None = None) -> None:
        try:
            safe_code = code if isinstance(code, DocumentStateErrorCode) else DocumentStateErrorCode(code)
        except ValueError as exc:
            raise ValueError("unsupported document state error code") from exc
        self.code = safe_code.value
        self.field = optional_string(field, "field", maximum=64)
        self.message = _SAFE_MESSAGES[safe_code]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "field": self.field}
