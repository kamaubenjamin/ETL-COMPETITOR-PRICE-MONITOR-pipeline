"""Sanitized adapter and export result contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .contracts import JsonContract, optional_id, optional_text, safe_code, safe_error_text, safe_metadata, stable_id, utc_timestamp
from .statuses import ExportStatus


_ADAPTER_TERMINAL = frozenset({ExportStatus.EXPORTED.value, ExportStatus.FAILED.value})
_RESULT_TERMINAL = frozenset(
    {
        ExportStatus.EXPORTED.value,
        ExportStatus.FAILED.value,
        ExportStatus.CANCELLED.value,
        ExportStatus.DUPLICATE_PREVENTED.value,
    }
)


@dataclass(frozen=True, slots=True)
class ExportAdapterResult(JsonContract):
    status: ExportStatus | str
    code: str
    retryable: bool
    message: str | None = None
    external_reference: str | None = None
    completed_at: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            status = ExportStatus(self.status).value
        except (TypeError, ValueError):
            raise ValueError("adapter result status is invalid") from None
        if status not in _ADAPTER_TERMINAL:
            raise ValueError("adapter result status must be terminal")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "code", safe_code(self.code, "code"))
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be a boolean")
        object.__setattr__(self, "message", None if self.message is None else safe_error_text(self.message))
        object.__setattr__(self, "external_reference", optional_id(self.external_reference, "external_reference"))
        if self.completed_at is not None:
            object.__setattr__(self, "completed_at", utc_timestamp(self.completed_at, "completed_at"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ExportResult(JsonContract):
    result_id: str
    attempt_id: str
    document_id: str
    target_id: str
    status: ExportStatus | str
    code: str
    occurred_at: str
    adapter_result: ExportAdapterResult | None = None
    duplicate_of_attempt_id: str | None = None
    lifecycle_decision_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_id", stable_id(self.result_id, "result_id"))
        object.__setattr__(self, "attempt_id", stable_id(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        object.__setattr__(self, "target_id", stable_id(self.target_id, "target_id"))
        try:
            status = ExportStatus(self.status).value
        except (TypeError, ValueError):
            raise ValueError("export result status is invalid") from None
        if status not in _RESULT_TERMINAL:
            raise ValueError("export result status must be terminal")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "code", safe_code(self.code, "code"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        if self.adapter_result is not None and not isinstance(self.adapter_result, ExportAdapterResult):
            raise ValueError("adapter_result must be an ExportAdapterResult")
        object.__setattr__(self, "duplicate_of_attempt_id", optional_id(self.duplicate_of_attempt_id, "duplicate_of_attempt_id"))
        object.__setattr__(self, "lifecycle_decision_id", optional_id(self.lifecycle_decision_id, "lifecycle_decision_id"))
        if status == ExportStatus.DUPLICATE_PREVENTED.value and self.duplicate_of_attempt_id is None:
            raise ValueError("duplicate_prevented requires duplicate_of_attempt_id")
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))

    @property
    def succeeded(self) -> bool:
        return self.status == ExportStatus.EXPORTED.value

