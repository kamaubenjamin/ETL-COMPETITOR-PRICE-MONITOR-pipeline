from concurrent.futures import ThreadPoolExecutor

import pytest

from src.export_runtime import (
    ExportAttempt,
    ExportRepositoryError,
    ExportTarget,
    InMemoryExportStore,
    generate_export_idempotency_key,
)


NOW = "2026-07-14T10:00:00Z"
LATER = "2026-07-14T10:01:00Z"


def attempt(attempt_id="attempt-001", *, status="ready", target_id="erp-main", fingerprint="a" * 64):
    target = ExportTarget(target_id, "erp", target_id)
    key = generate_export_idempotency_key(
        tenant_id="tenant-001", document_id="doc-001", export_target=target, payload_fingerprint=fingerprint
    )
    return ExportAttempt(
        attempt_id, "tenant-001", "doc-001", target, key, fingerprint, status, "export", "actor-001", NOW, NOW
    )


def test_status_update_uses_compare_and_swap_and_increments_version():
    store = InMemoryExportStore()
    store.writer.save_attempt(attempt())

    updated = store.writer.update_attempt_status("attempt-001", "preparing", expected_version=1, updated_at=LATER)

    assert updated.status == "preparing"
    assert updated.version == 2
    assert updated.updated_at == LATER
    assert store.reader.get_attempt("attempt-001") == updated


def test_stale_version_and_invalid_transition_are_safe_conflicts():
    store = InMemoryExportStore()
    store.writer.save_attempt(attempt())
    store.writer.update_attempt_status("attempt-001", "preparing", expected_version=1, updated_at=LATER)

    with pytest.raises(ExportRepositoryError) as stale:
        store.writer.update_attempt_status("attempt-001", "exporting", expected_version=1, updated_at=LATER)
    assert stale.value.code == "version_conflict"

    with pytest.raises(ExportRepositoryError) as invalid:
        store.writer.update_attempt_status("attempt-001", "exported", expected_version=2, updated_at=LATER)
    assert invalid.value.code == "invalid_transition"


def test_same_status_update_is_idempotent_and_terminal_status_cannot_advance():
    store = InMemoryExportStore()
    initial = attempt(status="exporting")
    store.writer.save_attempt(initial)
    assert store.writer.update_attempt_status("attempt-001", "exporting", expected_version=1, updated_at=LATER) is initial

    terminal = store.writer.update_attempt_status("attempt-001", "exported", expected_version=1, updated_at=LATER)
    with pytest.raises(ExportRepositoryError) as captured:
        store.writer.update_attempt_status("attempt-001", "failed", expected_version=terminal.version, updated_at=LATER)
    assert captured.value.code == "invalid_transition"


def test_active_duplicate_is_strictly_same_scope_target_and_key():
    store = InMemoryExportStore()
    active = attempt(status="preparing")
    store.writer.save_attempt(active)

    assert store.reader.has_active_duplicate(
        tenant_id="tenant-001", document_id="doc-001", target_id="erp-main", idempotency_key=active.idempotency_key
    )
    assert not store.reader.has_active_duplicate(
        tenant_id="tenant-001", document_id="doc-001", target_id="erp-other", idempotency_key=active.idempotency_key
    )
    changed = generate_export_idempotency_key(
        tenant_id="tenant-001", document_id="doc-001", export_target="erp-main", payload_fingerprint="b" * 64
    )
    assert not store.reader.has_active_duplicate(
        tenant_id="tenant-001", document_id="doc-001", target_id="erp-main", idempotency_key=changed
    )


def test_document_target_lock_is_optional_separate_helper_and_ignores_terminal_attempts():
    store = InMemoryExportStore()
    store.writer.save_attempt(attempt(status="preparing"))

    assert store.reader.has_active_document_target(tenant_id="tenant-001", document_id="doc-001", target_id="erp-main")
    assert not store.reader.has_active_document_target(tenant_id="tenant-001", document_id="doc-001", target_id="erp-other")

    store.writer.update_attempt_status("attempt-001", "failed", expected_version=1, updated_at=LATER)
    assert not store.reader.has_active_document_target(tenant_id="tenant-001", document_id="doc-001", target_id="erp-main")


def test_concurrent_equal_idempotency_claims_cannot_both_succeed():
    store = InMemoryExportStore()
    candidates = (attempt("attempt-001", status="preparing"), attempt("attempt-002", status="preparing"))

    def claim(record):
        try:
            store.writer.save_attempt(record)
            return "saved"
        except ExportRepositoryError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(claim, candidates))

    assert outcomes == ["duplicate_idempotency_key", "saved"]
    assert store.reader.list_attempts().total == 1
