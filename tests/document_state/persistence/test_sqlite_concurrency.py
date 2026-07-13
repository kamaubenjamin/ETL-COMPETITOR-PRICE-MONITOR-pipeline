from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

from src.document_state import AuditEventRecord, AuditQuery, DocumentRecord, PageRequest
from src.document_state.errors import DocumentStateError
from src.document_state.persistence import PersistenceConfig
from src.document_state.persistence.sqlite import SQLiteDocumentStateRepositories


TS1 = "2026-07-13T09:00:00+00:00"
TS2 = "2026-07-13T10:00:00+00:00"


def _store(tmp_path):
    return SQLiteDocumentStateRepositories(
        PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "concurrency.sqlite3"))
    )


def _outcome(operation):
    try:
        return "success", operation()
    except DocumentStateError as error:
        return error.code, None


def test_two_same_version_updates_cannot_both_succeed(tmp_path):
    store = _store(tmp_path)
    original = DocumentRecord("doc-001", "invoice.pdf", "invoice", "validated", 0.95, "validate_data", TS1, TS1, TS1)
    store.writer.create_document(original)
    candidates = (
        replace(original, status="approved", updated_at=TS2, version=2),
        replace(original, status="export_ready", updated_at=TS2, version=2),
    )
    barrier = Barrier(2)

    def update(candidate):
        barrier.wait()
        return _outcome(lambda: store.writer.update_document(candidate, expected_version=1))

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(update, candidates))

    assert sorted(code for code, _ in outcomes) == ["conflict", "success"]
    persisted = store.reader.get_document("doc-001")
    assert persisted.version == 2
    assert persisted.status in {"approved", "export_ready"}


def test_concurrent_identical_append_is_idempotent(tmp_path):
    store = _store(tmp_path)
    event = AuditEventRecord("audit-001", "document_validated", "workflow", TS1, document_id="doc-001")
    barrier = Barrier(2)

    def append():
        barrier.wait()
        return _outcome(lambda: store.writer.append_audit_event(event, idempotency_key="audit-idem"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: append(), range(2)))

    assert [code for code, _ in outcomes] == ["success", "success"]
    assert all(value == event for _, value in outcomes)
    assert store.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1


def test_concurrent_conflicting_idempotency_key_has_one_winner(tmp_path):
    store = _store(tmp_path)
    events = (
        AuditEventRecord("audit-001", "document_validated", "workflow", TS1, document_id="doc-001"),
        AuditEventRecord("audit-002", "document_failed", "workflow", TS1, document_id="doc-002"),
    )
    barrier = Barrier(2)

    def append(event):
        barrier.wait()
        return _outcome(lambda: store.writer.append_audit_event(event, idempotency_key="shared-idem"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(append, events))

    assert sorted(code for code, _ in outcomes) == ["conflict", "success"]
    assert store.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1
