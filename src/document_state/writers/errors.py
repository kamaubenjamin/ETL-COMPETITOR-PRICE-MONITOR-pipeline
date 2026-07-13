"""Privacy-safe errors for Document State writer contracts."""

from __future__ import annotations

from enum import Enum

from ..privacy import optional_string


class WriterErrorCode(str, Enum):
    INVALID_COMMAND = "invalid_command"
    INVALID_MAPPING = "invalid_mapping"
    INVALID_IDEMPOTENCY_KEY = "invalid_idempotency_key"
    VERSION_CONFLICT = "version_conflict"
    REPOSITORY_UNAVAILABLE = "repository_unavailable"
    INTERNAL_ERROR = "internal_error"


_SAFE_MESSAGES = {
    WriterErrorCode.INVALID_COMMAND: "Document State writer command is invalid.",
    WriterErrorCode.INVALID_MAPPING: "Document State writer mapping is invalid.",
    WriterErrorCode.INVALID_IDEMPOTENCY_KEY: "Document State writer idempotency key is invalid.",
    WriterErrorCode.VERSION_CONFLICT: "Document State writer version conflict was detected.",
    WriterErrorCode.REPOSITORY_UNAVAILABLE: "Document State repository is unavailable.",
    WriterErrorCode.INTERNAL_ERROR: "Document State writer operation could not be completed.",
}


class DocumentStateWriterError(Exception):
    def __init__(self, code: WriterErrorCode | str, *, field: str | None = None) -> None:
        try:
            safe_code = code if isinstance(code, WriterErrorCode) else WriterErrorCode(code)
        except ValueError as exc:
            raise ValueError("unsupported writer error code") from exc
        self.code = safe_code.value
        self.field = optional_string(field, "field", maximum=64)
        self.message = _SAFE_MESSAGES[safe_code]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "field": self.field}
