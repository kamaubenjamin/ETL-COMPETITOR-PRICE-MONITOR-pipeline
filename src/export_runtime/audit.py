"""Pure creation of bounded export audit intents."""

from __future__ import annotations

from typing import Any

from .commands import ExportRuntimeCommand
from .contracts import ExportAuditIntent


def create_export_audit_intent(
    command: ExportRuntimeCommand,
    *,
    event_type: str,
    outcome_code: str,
    occurred_at: str,
    attempt_id: str | None = None,
    result_status: str | None = None,
) -> ExportAuditIntent:
    if not isinstance(command, ExportRuntimeCommand):
        raise ValueError("command must be an ExportRuntimeCommand")
    metadata: dict[str, Any] = {
        "tenant_id": command.tenant_id,
        "target_type": command.target.target_type,
        "target_label": command.target.display_label,
    }
    if command.correlation_id is not None:
        metadata["correlation_id"] = command.correlation_id
    if command.request_id is not None:
        metadata["request_id"] = command.request_id
    if result_status is not None:
        metadata["result_status"] = result_status
    return ExportAuditIntent(
        event_type=event_type,
        document_id=command.document_id,
        target_id=command.target.target_id,
        actor_id=command.actor_id,
        occurred_at=occurred_at,
        outcome_code=outcome_code,
        attempt_id=attempt_id,
        metadata=metadata,
    )
