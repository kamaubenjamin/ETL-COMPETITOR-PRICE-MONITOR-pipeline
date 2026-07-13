"""Privacy-safe errors for lifecycle policy and advancement contracts."""

from __future__ import annotations

from enum import Enum

from ..privacy import optional_string


class LifecycleErrorCode(str, Enum):
    INVALID_TRANSITION = "invalid_transition"
    INVALID_REQUEST = "invalid_request"
    VERSION_CONFLICT = "version_conflict"
    MISSING_DOCUMENT = "missing_document"
    REPOSITORY_UNAVAILABLE = "repository_unavailable"
    INTERNAL_ERROR = "internal_error"


_SAFE_MESSAGES = {
    LifecycleErrorCode.INVALID_TRANSITION: "Lifecycle transition is not allowed.",
    LifecycleErrorCode.INVALID_REQUEST: "Lifecycle transition request is invalid.",
    LifecycleErrorCode.VERSION_CONFLICT: "Lifecycle projection version conflict was detected.",
    LifecycleErrorCode.MISSING_DOCUMENT: "Lifecycle document was not found.",
    LifecycleErrorCode.REPOSITORY_UNAVAILABLE: "Lifecycle repository is unavailable.",
    LifecycleErrorCode.INTERNAL_ERROR: "Lifecycle operation could not be completed.",
}


class LifecyclePolicyError(Exception):
    def __init__(self, code: LifecycleErrorCode | str, *, field: str | None = None) -> None:
        try:
            safe_code = code if isinstance(code, LifecycleErrorCode) else LifecycleErrorCode(code)
        except (TypeError, ValueError) as exc:
            raise ValueError("unsupported lifecycle error code") from exc
        self.code = safe_code.value
        self.field = optional_string(field, "field", maximum=64)
        self.message = _SAFE_MESSAGES[safe_code]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "field": self.field}
