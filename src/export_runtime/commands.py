"""Safe caller-supplied command for internal export orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .builder import ExportPayloadBuildCommand
from .contracts import ExportTarget, JsonContract, optional_id, optional_timestamp, positive_integer, safe_metadata, stable_id
from .readiness import ExportReadinessResult
from .statuses import ExportOperationType


@dataclass(frozen=True, slots=True)
class ExportRuntimeCommand(JsonContract):
    tenant_id: str
    actor_id: str
    document_id: str
    target: ExportTarget
    payload_command: ExportPayloadBuildCommand
    readiness: ExportReadinessResult
    operation_type: ExportOperationType | str = ExportOperationType.EXPORT
    operation_version: str = "v1"
    requested_at: str | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "actor_id", stable_id(self.actor_id, "actor_id"))
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        if not isinstance(self.target, ExportTarget):
            raise ValueError("target must be an ExportTarget")
        if not isinstance(self.payload_command, ExportPayloadBuildCommand):
            raise ValueError("payload_command must be an ExportPayloadBuildCommand")
        if not isinstance(self.readiness, ExportReadinessResult):
            raise ValueError("readiness must be an ExportReadinessResult")
        try:
            operation_type = ExportOperationType(self.operation_type).value
        except (TypeError, ValueError):
            raise ValueError("operation_type is invalid") from None
        object.__setattr__(self, "operation_type", operation_type)
        object.__setattr__(self, "operation_version", stable_id(self.operation_version, "operation_version"))
        object.__setattr__(self, "requested_at", optional_timestamp(self.requested_at, "requested_at"))
        object.__setattr__(self, "correlation_id", optional_id(self.correlation_id, "correlation_id"))
        object.__setattr__(self, "request_id", optional_id(self.request_id, "request_id"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))

        payload_document = stable_id(self.payload_command.document_id, "payload_document_id")
        payload_tenant = stable_id(self.payload_command.tenant_id, "payload_tenant_id")
        positive_integer(self.payload_command.document_version, "document_version")
        payload_target = self.payload_command.export_target
        if self.readiness.document_id != self.document_id or payload_document != self.document_id:
            raise ValueError("document identity is inconsistent")
        if payload_tenant != self.tenant_id:
            raise ValueError("tenant identity is inconsistent")
        if not isinstance(payload_target, ExportTarget) or payload_target.target_id != self.target.target_id:
            raise ValueError("target identity is inconsistent")
        if self.readiness.target is not None and self.readiness.target.target_id != self.target.target_id:
            raise ValueError("readiness target is inconsistent")
