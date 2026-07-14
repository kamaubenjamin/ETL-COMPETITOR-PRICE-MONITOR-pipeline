"""Pure payload/idempotency policy helpers for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass

from .builder import ExportPayloadBuildResult
from .contracts import ExportTarget, stable_id
from .fingerprints import fingerprint_export_payload
from .idempotency import ExportIdempotencyKey, generate_export_idempotency_key
from .payloads import ExportPayload
from .readiness import ExportReadinessIssue
from .statuses import ExportOperationType


@dataclass(frozen=True, slots=True)
class ExportIdempotencyPolicy:
    operation_type: ExportOperationType | str = ExportOperationType.EXPORT
    operation_version: str = "v1"

    def __post_init__(self) -> None:
        try:
            operation_type = (
                self.operation_type.value
                if isinstance(self.operation_type, ExportOperationType)
                else ExportOperationType(self.operation_type).value
            )
        except (TypeError, ValueError):
            raise ValueError("operation_type is invalid") from None
        object.__setattr__(self, "operation_type", operation_type)
        object.__setattr__(self, "operation_version", stable_id(self.operation_version, "operation_version"))

    def key_for_inputs(
        self,
        *,
        tenant_id: str,
        document_id: str,
        export_target: ExportTarget | str,
        payload_fingerprint: str,
    ) -> ExportIdempotencyKey:
        return generate_export_idempotency_key(
            tenant_id=tenant_id,
            document_id=document_id,
            export_target=export_target,
            payload_fingerprint=payload_fingerprint,
            operation_type=self.operation_type,
            operation_version=self.operation_version,
        )

    def key_for_payload(self, payload: ExportPayload) -> ExportIdempotencyKey:
        if not isinstance(payload, ExportPayload):
            raise ValueError("payload must be an ExportPayload")
        return self.key_for_inputs(
            tenant_id=payload.tenant_id,
            document_id=payload.document_id,
            export_target=payload.export_target,
            payload_fingerprint=fingerprint_export_payload(payload),
        )


def payload_invalid_readiness_issue() -> ExportReadinessIssue:
    return ExportReadinessIssue("payload_invalid", field="payload")


def payload_readiness_issues(result: ExportPayloadBuildResult) -> tuple[ExportReadinessIssue, ...]:
    if not isinstance(result, ExportPayloadBuildResult):
        raise ValueError("result must be an ExportPayloadBuildResult")
    return () if result.succeeded else (result.readiness_issue,)
