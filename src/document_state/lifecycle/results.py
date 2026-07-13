"""Serializable outcomes for lifecycle projection operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..contracts import DocumentStatus
from ..privacy import enum_value, positive_version, stable_id
from .errors import LifecycleErrorCode


class LifecycleResultStatus(str, Enum):
    ADVANCED = "advanced"
    NO_OP = "no_op"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    PROJECTION_PENDING = "projection_pending"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class LifecycleTransitionResult:
    status: LifecycleResultStatus | str
    document_id: str
    lifecycle_event_id: str
    source_status: DocumentStatus | str
    target_status: DocumentStatus | str
    expected_version: int
    new_version: int | None = None
    error_code: LifecycleErrorCode | str | None = None

    def __post_init__(self) -> None:
        try:
            status = self.status.value if isinstance(self.status, LifecycleResultStatus) else LifecycleResultStatus(self.status).value
        except (TypeError, ValueError) as exc:
            raise ValueError("status is invalid") from exc
        object.__setattr__(self, "status", status)
        for name in ("document_id", "lifecycle_event_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        for name in ("source_status", "target_status"):
            object.__setattr__(self, name, enum_value(getattr(self, name), DocumentStatus, name))
        expected = positive_version(self.expected_version)
        object.__setattr__(self, "expected_version", expected)
        new_version = None if self.new_version is None else positive_version(self.new_version)
        object.__setattr__(self, "new_version", new_version)
        if self.error_code is None:
            error_code = None
        else:
            try:
                error_code = self.error_code.value if isinstance(self.error_code, LifecycleErrorCode) else LifecycleErrorCode(self.error_code).value
            except (TypeError, ValueError) as exc:
                raise ValueError("error_code is invalid") from exc
        object.__setattr__(self, "error_code", error_code)

        successful = status in {LifecycleResultStatus.ADVANCED.value, LifecycleResultStatus.NO_OP.value}
        if successful and error_code is not None:
            raise ValueError("successful results cannot contain an error_code")
        if not successful and error_code is None:
            raise ValueError("non-successful results require an error_code")
        if status == LifecycleResultStatus.ADVANCED.value and new_version != expected + 1:
            raise ValueError("advanced result requires expected_version + 1")
        if status == LifecycleResultStatus.NO_OP.value and new_version not in {None, expected}:
            raise ValueError("no_op result cannot advance the version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "document_id": self.document_id,
            "lifecycle_event_id": self.lifecycle_event_id,
            "source_status": self.source_status,
            "target_status": self.target_status,
            "expected_version": self.expected_version,
            "new_version": self.new_version,
            "error_code": self.error_code,
        }
