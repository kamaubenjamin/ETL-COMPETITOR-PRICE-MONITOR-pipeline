"""Serializable outcomes for internal Document State writer operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..privacy import bounded_string, non_negative_count, optional_string, stable_id
from .errors import WriterErrorCode


class WriterResultStatus(str, Enum):
    SUCCESS = "success"
    SKIPPED_IDEMPOTENT = "skipped_idempotent"
    PROJECTION_PENDING = "projection_pending"
    CONFLICT = "conflict"
    INVALID_INPUT = "invalid_input"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class WriterResult:
    status: WriterResultStatus | str
    operation: str
    record_ids: tuple[str, ...] = ()
    committed_count: int = 0
    error_code: WriterErrorCode | str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        try:
            status = self.status.value if isinstance(self.status, WriterResultStatus) else WriterResultStatus(self.status).value
        except (TypeError, ValueError) as exc:
            raise ValueError("status is invalid") from exc
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "operation", bounded_string(self.operation, "operation", maximum=128))
        object.__setattr__(self, "record_ids", tuple(stable_id(item, "record_id") for item in self.record_ids))
        object.__setattr__(self, "committed_count", non_negative_count(self.committed_count, "committed_count"))
        if self.committed_count > len(self.record_ids):
            raise ValueError("committed_count cannot exceed record_ids")
        if self.error_code is None:
            error_code = None
        else:
            try:
                error_code = self.error_code.value if isinstance(self.error_code, WriterErrorCode) else WriterErrorCode(self.error_code).value
            except (TypeError, ValueError) as exc:
                raise ValueError("error_code is invalid") from exc
        object.__setattr__(self, "error_code", error_code)
        object.__setattr__(self, "message", optional_string(self.message, "message"))
        successful = status in {WriterResultStatus.SUCCESS.value, WriterResultStatus.SKIPPED_IDEMPOTENT.value}
        if successful and (error_code is not None or self.message is not None):
            raise ValueError("successful results cannot contain errors")
        if not successful and error_code is None:
            raise ValueError("non-successful results require an error_code")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "operation": self.operation,
            "record_ids": list(self.record_ids),
            "committed_count": self.committed_count,
            "error_code": self.error_code,
            "message": self.message,
        }
