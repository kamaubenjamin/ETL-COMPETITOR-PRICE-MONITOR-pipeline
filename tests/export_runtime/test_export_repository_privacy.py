import json

import pytest

from src.export_runtime import (
    ExportAdapterResult,
    ExportAttempt,
    ExportRepositoryError,
    ExportResult,
    ExportTarget,
    InMemoryExportStore,
    generate_export_idempotency_key,
)


NOW = "2026-07-14T10:00:00Z"
FORBIDDEN = {
    "raw_document",
    "raw_rows",
    "raw_correction_value",
    "artifact_payload",
    "adapter_response",
    "credential",
    "token",
    "claim",
    "backend_path",
    "stack_trace",
}


def safe_attempt(metadata=None):
    target = ExportTarget("erp-main", "erp", "Main ERP")
    key = generate_export_idempotency_key(
        tenant_id="tenant-001", document_id="doc-001", export_target=target, payload_fingerprint="a" * 64
    )
    return ExportAttempt(
        "attempt-001", "tenant-001", "doc-001", target, key, "a" * 64, "preparing", "export", "actor-001", NOW, NOW,
        metadata={} if metadata is None else metadata,
    )


@pytest.mark.parametrize("key", sorted(FORBIDDEN))
def test_attempt_metadata_rejects_sensitive_or_raw_fields_before_storage(key):
    with pytest.raises(ValueError):
        safe_attempt({key: "private"})


def test_adapter_result_rejects_raw_vendor_response_metadata():
    with pytest.raises(ValueError):
        ExportAdapterResult("failed", "rejected", False, metadata={"vendor_response": "raw body"})


def test_repository_projection_contains_only_safe_contract_fields():
    store = InMemoryExportStore()
    record = safe_attempt({"retry_count": 0})
    store.writer.save_attempt(record)
    adapter = ExportAdapterResult("failed", "rejected", True, message="Adapter did not confirm success.", completed_at=NOW)
    result = ExportResult("result-001", "attempt-001", "doc-001", "erp-main", "failed", "rejected", NOW, adapter_result=adapter)
    store.writer.save_result(result)

    projected = json.dumps(
        {
            "attempts": store.reader.list_attempts().to_dict(),
            "results": store.reader.list_results_by_attempt("attempt-001").to_dict(),
        }
    ).lower()
    assert not any(key in projected for key in FORBIDDEN)
    assert "adapter did not confirm success" in projected


def test_repository_errors_never_echo_identifiers_or_raw_details():
    store = InMemoryExportStore()
    private_id = "private-attempt-123"
    with pytest.raises(ExportRepositoryError) as captured:
        store.reader.get_attempt(private_id)

    serialized = json.dumps(captured.value.to_dict())
    assert private_id not in serialized
    assert captured.value.code == "not_found"

