"""Immutable export attempt contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .contracts import ExportTarget, JsonContract, fingerprint, non_negative_integer, optional_id, positive_integer, safe_metadata, stable_id, utc_timestamp
from .idempotency import ExportIdempotencyKey
from .statuses import ExportOperationStatus, ExportOperationType


@dataclass(frozen=True, slots=True)
class ExportAttempt(JsonContract):
    attempt_id: str
    tenant_id: str
    document_id: str
    target: ExportTarget
    idempotency_key: ExportIdempotencyKey
    payload_fingerprint: str
    status: ExportOperationStatus | str
    operation_type: ExportOperationType | str
    requested_by: str
    created_at: str
    updated_at: str
    operation_version: str = "v1"
    version: int = 1
    retry_of_attempt_id: str | None = None
    retry_ordinal: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempt_id", stable_id(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        if not isinstance(self.target, ExportTarget):
            raise ValueError("target must be an ExportTarget")
        if not isinstance(self.idempotency_key, ExportIdempotencyKey):
            raise ValueError("idempotency_key must be an ExportIdempotencyKey")
        object.__setattr__(self, "payload_fingerprint", fingerprint(self.payload_fingerprint))
        try:
            object.__setattr__(self, "status", ExportOperationStatus(self.status).value)
            object.__setattr__(self, "operation_type", ExportOperationType(self.operation_type).value)
        except (TypeError, ValueError):
            raise ValueError("attempt status or operation type is invalid") from None
        object.__setattr__(self, "requested_by", stable_id(self.requested_by, "requested_by"))
        object.__setattr__(self, "created_at", utc_timestamp(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", utc_timestamp(self.updated_at, "updated_at"))
        object.__setattr__(self, "operation_version", stable_id(self.operation_version, "operation_version"))
        object.__setattr__(self, "version", positive_integer(self.version, "version"))
        object.__setattr__(self, "retry_of_attempt_id", optional_id(self.retry_of_attempt_id, "retry_of_attempt_id"))
        object.__setattr__(self, "retry_ordinal", non_negative_integer(self.retry_ordinal, "retry_ordinal"))
        if self.retry_ordinal and self.retry_of_attempt_id is None:
            raise ValueError("retry_ordinal requires retry_of_attempt_id")
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))

