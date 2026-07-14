import json

import pytest

from src.export_runtime import (
    ExportAdapterResult,
    ExportAttempt,
    ExportAuditIntent,
    ExportLifecycleDecision,
    ExportResult,
    ExportTarget,
    generate_export_idempotency_key,
)


FINGERPRINT = "a" * 64
TIMESTAMP = "2026-07-14T10:00:00Z"


def target() -> ExportTarget:
    return ExportTarget("erp-main", "erp", "Main ERP")


def key():
    return generate_export_idempotency_key(
        tenant_id="tenant-001",
        document_id="doc-001",
        export_target="erp-main",
        payload_fingerprint=FINGERPRINT,
    )


def test_attempt_serializes_without_raw_payload():
    attempt = ExportAttempt(
        attempt_id="attempt-001",
        tenant_id="tenant-001",
        document_id="doc-001",
        target=target(),
        idempotency_key=key(),
        payload_fingerprint=FINGERPRINT,
        status="preparing",
        operation_type="export",
        requested_by="actor-001",
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
        metadata={"request_id": "req-001"},
    )
    encoded = json.dumps(attempt.to_dict())
    assert "attempt-001" in encoded
    assert "raw_document" not in encoded


def test_retry_attempt_requires_parent_reference():
    with pytest.raises(ValueError, match="retry_ordinal"):
        ExportAttempt(
            "attempt-002", "tenant-001", "doc-001", target(), key(), FINGERPRINT,
            "preparing", "retry", "actor-001", TIMESTAMP, TIMESTAMP, retry_ordinal=1,
        )


def test_adapter_and_export_results_are_sanitized_and_terminal():
    adapter = ExportAdapterResult(
        status="exported",
        code="accepted",
        retryable=False,
        message="Export target confirmed receipt.",
        external_reference="erp-ref-001",
        completed_at=TIMESTAMP,
    )
    result = ExportResult(
        "result-001", "attempt-001", "doc-001", "erp-main", "exported", "confirmed", TIMESTAMP,
        adapter_result=adapter,
    )
    assert result.succeeded is True
    assert result.to_dict()["adapter_result"]["external_reference"] == "erp-ref-001"

    with pytest.raises(ValueError, match="terminal"):
        ExportAdapterResult("exporting", "started", False)


def test_adapter_failure_rejects_raw_exception_or_path_text():
    with pytest.raises(ValueError, match="unsafe details"):
        ExportAdapterResult("failed", "adapter_failed", True, message="Traceback (most recent call last): secret")
    with pytest.raises(ValueError, match="unsafe details"):
        ExportAdapterResult("failed", "adapter_failed", True, message=r"Failed at C:\private\adapter.py")


def test_duplicate_result_requires_safe_attempt_reference():
    with pytest.raises(ValueError, match="duplicate_of_attempt_id"):
        ExportResult("result-002", "attempt-002", "doc-001", "erp-main", "duplicate_prevented", "duplicate", TIMESTAMP)


def test_lifecycle_and_audit_intents_are_json_safe():
    lifecycle = ExportLifecycleDecision(True, "exported", 4, "adapter_confirmed")
    audit = ExportAuditIntent(
        "export_succeeded", "doc-001", "erp-main", "actor-001", TIMESTAMP, "confirmed",
        attempt_id="attempt-001", metadata={"retry_ordinal": 0},
    )
    assert lifecycle.to_dict()["target_status"] == "exported"
    assert json.loads(json.dumps(audit.to_dict()))["event_type"] == "export_succeeded"

