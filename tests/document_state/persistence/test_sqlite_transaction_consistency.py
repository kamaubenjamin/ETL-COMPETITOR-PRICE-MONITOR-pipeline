import pytest

from src.document_state import AuditEventRecord, AuditQuery, DocumentQuery, DocumentRecord, PageRequest
from src.document_state.errors import DocumentStateError
from src.document_state.persistence import PersistenceConfig
from src.document_state.persistence.sqlite import (
    SQLiteConnectionFactory,
    SQLiteDocumentStateRepositories,
    apply_migrations,
)


TS = "2026-07-13T09:00:00+00:00"


def _config(tmp_path):
    return PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "transactions.sqlite3"))


def _document(suffix):
    return DocumentRecord(f"doc-{suffix}", f"invoice-{suffix}.pdf", "invoice", "validated", 0.95, "validate_data", TS, TS, TS)


def test_records_survive_reopen_and_migration_rerun(tmp_path):
    config = _config(tmp_path)
    first = SQLiteDocumentStateRepositories(config)
    first.writer.create_document(_document("001"))

    apply_migrations(SQLiteConnectionFactory(config))
    reopened = SQLiteDocumentStateRepositories(config)
    assert reopened.reader.get_document("doc-001") == _document("001")
    assert reopened.reader.list_documents(DocumentQuery(), PageRequest()).total == 1


def test_failed_append_transaction_leaves_no_record_or_idempotency_state(tmp_path):
    config = _config(tmp_path)
    store = SQLiteDocumentStateRepositories(config)
    factory = SQLiteConnectionFactory(config)
    with factory.transaction(write=True) as connection:
        connection.execute(
            "CREATE TRIGGER reject_audit AFTER INSERT ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'rejected'); END"
        )

    event = AuditEventRecord("audit-001", "document_validated", "workflow", TS, document_id="doc-001")
    with pytest.raises(DocumentStateError) as rejected:
        store.writer.append_audit_event(event, idempotency_key="audit-idem")
    assert rejected.value.code == "conflict"
    assert "rejected" not in str(rejected.value).lower()
    assert store.reader.list_audit_events(AuditQuery(), PageRequest()).total == 0

    with factory.transaction(write=True) as connection:
        connection.execute("DROP TRIGGER reject_audit")
    assert store.writer.append_audit_event(event, idempotency_key="audit-idem") == event


def test_sqlite_read_transaction_keeps_count_and_page_snapshot_consistent(tmp_path):
    config = _config(tmp_path)
    store = SQLiteDocumentStateRepositories(config)
    store.writer.create_document(_document("001"))
    factory = SQLiteConnectionFactory(config)

    with factory.transaction() as reader_connection:
        total_before = reader_connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        store.writer.create_document(_document("002"))
        rows = reader_connection.execute(
            "SELECT document_id FROM documents ORDER BY received_at, document_id LIMIT 50 OFFSET 0"
        ).fetchall()
        total_after = reader_connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    assert total_before == total_after == len(rows) == 1
    assert store.reader.list_documents(DocumentQuery(), PageRequest()).total == 2
