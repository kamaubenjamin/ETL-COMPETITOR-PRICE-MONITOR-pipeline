"""Pure export lifecycle intent policy; no projection mutation occurs here."""

from __future__ import annotations

from .contracts import ExportLifecycleDecision, positive_integer


def export_lifecycle_decision(*, outcome: str, document_version: int) -> ExportLifecycleDecision:
    version = positive_integer(document_version, "document_version")
    if outcome == "exported":
        return ExportLifecycleDecision(True, "exported", version, "export_confirmed")
    reason_by_outcome = {
        "not_ready": "not_ready",
        "duplicate_prevented": "duplicate_prevented",
        "adapter_unavailable": "adapter_unavailable",
        "failed": "export_failed",
        "invalid_payload": "payload_invalid",
        "repository_error": "repository_error",
    }
    try:
        reason = reason_by_outcome[outcome]
    except KeyError:
        raise ValueError("lifecycle outcome is invalid") from None
    return ExportLifecycleDecision(False, "unchanged", version, reason)
