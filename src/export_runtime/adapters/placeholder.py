"""Test/dev adapter placeholders that make no external call."""

from __future__ import annotations

from ..fingerprints import fingerprint_export_payload
from ..payloads import ExportPayload
from ..results import ExportAdapterResult


class SuccessfulPlaceholderAdapter:
    def export(self, payload: ExportPayload) -> ExportAdapterResult:
        if not isinstance(payload, ExportPayload):
            raise ValueError("payload must be an ExportPayload")
        reference = f"placeholder-{fingerprint_export_payload(payload)[:16]}"
        return ExportAdapterResult(
            status="exported",
            code="placeholder_confirmed",
            retryable=False,
            message="Placeholder adapter confirmed export.",
            external_reference=reference,
            metadata={"adapter_mode": "placeholder"},
        )


class FailingPlaceholderAdapter:
    def export(self, payload: ExportPayload) -> ExportAdapterResult:
        if not isinstance(payload, ExportPayload):
            raise ValueError("payload must be an ExportPayload")
        return ExportAdapterResult(
            status="failed",
            code="placeholder_failed",
            retryable=True,
            message="Placeholder adapter did not confirm export.",
            metadata={"adapter_mode": "placeholder"},
        )


class UnavailablePlaceholderAdapter:
    def export(self, payload: ExportPayload) -> ExportAdapterResult:
        if not isinstance(payload, ExportPayload):
            raise ValueError("payload must be an ExportPayload")
        return ExportAdapterResult(
            status="failed",
            code="adapter_unavailable",
            retryable=True,
            message="Export adapter is unavailable.",
            metadata={"adapter_mode": "placeholder"},
        )
