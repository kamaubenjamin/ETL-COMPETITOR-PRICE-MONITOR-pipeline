"""Fixed privacy-safe upload errors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import UploadContract


class UploadErrorCode(str, Enum):
    INVALID_COMMAND = "invalid_command"
    VALIDATION_FAILED = "validation_failed"
    DUPLICATE_PREVENTED = "duplicate_prevented"
    STAGING_UNAVAILABLE = "staging_unavailable"
    STAGING_FAILED = "staging_failed"
    INTERNAL_ERROR = "internal_error"


_MESSAGES = {
    UploadErrorCode.INVALID_COMMAND: "Upload command is invalid.",
    UploadErrorCode.VALIDATION_FAILED: "Upload validation failed.",
    UploadErrorCode.DUPLICATE_PREVENTED: "An equivalent upload is already active.",
    UploadErrorCode.STAGING_UNAVAILABLE: "Upload staging is unavailable.",
    UploadErrorCode.STAGING_FAILED: "Upload could not be staged.",
    UploadErrorCode.INTERNAL_ERROR: "Upload could not be completed.",
}


@dataclass(frozen=True, slots=True)
class UploadError(UploadContract, Exception):
    code: UploadErrorCode | str
    field: str | None = None
    message: str = ""

    def __post_init__(self) -> None:
        try:
            code = self.code if isinstance(self.code, UploadErrorCode) else UploadErrorCode(self.code)
        except (TypeError, ValueError):
            raise ValueError("upload error code is invalid") from None
        object.__setattr__(self, "code", code.value)
        if self.field is not None and (not isinstance(self.field, str) or not self.field or len(self.field) > 64):
            raise ValueError("field is invalid")
        object.__setattr__(self, "message", _MESSAGES[code])
        Exception.__init__(self, self.message)

