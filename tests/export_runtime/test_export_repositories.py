from dataclasses import FrozenInstanceError

import pytest

from src.export_runtime import (
    ExportAdapterResult,
    ExportAttempt,
    ExportRepositoryError,
    ExportRepositoryReader,
    ExportRepositoryWriter,
    ExportResult,
    ExportTarget,
    InMemoryExportStore,
    generate_export_idempotency_key,
)


NOW = "2026-07-14T10:00:00Z"


def attempt(attempt_id="attempt-001", *, target_id="erp-main", fingerprint="a" * 64, status="preparing"):
    target = ExportTarget(target_id, "erp", target_id)
    key = generate_export_idempotency_key(
        tenant_id="tenant-001",
        document_id="doc-001",
        export_target=target,
        payload_fingerprint=fingerprint,
    )
    return ExportAttempt(
        attempt_id,
        "tenant-001",
        "doc-001",
        target,
        key,
        fingerprint,
        status,
        "export",
        "actor-001",
        NOW,
        NOW,
    )


def result(result_id="result-001", *, attempt_id="attempt-001", status="exported"):
    adapter = ExportAdapterResult(status, "confirmed" if status == "exported" else "rejected", False, completed_at=NOW)
    return ExportResult(result_id, attempt_id, "doc-001", "erp-main", status, "confirmed", NOW, adapter_result=adapter)


def test_store_views_satisfy_read_and_write_protocols():
    store = InMemoryExportStore()
    assert isinstance(store.reader, ExportRepositoryReader)
    assert isinstance(store.writer, ExportRepositoryWriter)


def test_can_save_and_read_attempt_by_id_and_idempotency_key():
    store = InMemoryExportStore()
    record = attempt()

    assert store.writer.save_attempt(record) is record
    assert store.reader.get_attempt(record.attempt_id) is record
    assert store.reader.get_attempt_by_idempotency_key(record.idempotency_key) is record
    with pytest.raises(FrozenInstanceError):
        record.status = "failed"


def test_duplicate_attempt_id_is_rejected_safely():
    store = InMemoryExportStore()
    store.writer.save_attempt(attempt())

    with pytest.raises(ExportRepositoryError) as captured:
        store.writer.save_attempt(attempt(fingerprint="b" * 64))
    assert captured.value.code == "duplicate_attempt"


def test_duplicate_idempotency_key_is_rejected_safely():
    store = InMemoryExportStore()
    first = attempt()
    store.writer.save_attempt(first)

    with pytest.raises(ExportRepositoryError) as captured:
        store.writer.save_attempt(attempt("attempt-002"))
    assert captured.value.code == "duplicate_idempotency_key"


def test_can_save_and_list_terminal_result_for_existing_attempt():
    store = InMemoryExportStore()
    store.writer.save_attempt(attempt())
    terminal = result()

    assert store.writer.save_result(terminal) is terminal
    page = store.reader.list_results_by_attempt("attempt-001")
    assert page.items == (terminal,)
    assert page.total == 1


def test_result_for_missing_attempt_is_rejected():
    store = InMemoryExportStore()
    with pytest.raises(ExportRepositoryError) as captured:
        store.writer.save_result(result())
    assert captured.value.code == "missing_attempt"


def test_terminal_result_cannot_be_overwritten_or_duplicated():
    store = InMemoryExportStore()
    store.writer.save_attempt(attempt())
    store.writer.save_result(result())

    with pytest.raises(ExportRepositoryError) as captured:
        store.writer.save_result(result("result-002", status="failed"))
    assert captured.value.code == "terminal_result_exists"


def test_result_identity_must_match_owning_attempt():
    store = InMemoryExportStore()
    store.writer.save_attempt(attempt())
    mismatched = ExportResult("result-001", "attempt-001", "doc-002", "erp-main", "failed", "rejected", NOW)

    with pytest.raises(ExportRepositoryError) as captured:
        store.writer.save_result(mismatched)
    assert captured.value.code == "invalid_record"

