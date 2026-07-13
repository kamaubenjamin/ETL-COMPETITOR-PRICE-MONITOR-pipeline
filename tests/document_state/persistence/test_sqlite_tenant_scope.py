import pytest

from src.document_state import DocumentQuery, DocumentRecord, DocumentStateError, PageRequest
from src.document_state.persistence import PersistenceConfig
from src.document_state.persistence.sqlite import SQLiteDocumentStateRepositories


TS = "2026-07-13T12:00:00+00:00"


def _document(document_id, tenant_id):
    return DocumentRecord(
        document_id, f"{document_id}.pdf", "invoice", "received", 0.9,
        "ingest", TS, TS, TS,
        tenant_id=tenant_id,
        workspace_id=f"workspace-{tenant_id[-1]}",
        created_by="principal-create",
        source_system="upload_runtime",
        access_tags=("finance",),
    )


def test_sqlite_persists_filters_and_reopens_tenant_scope(tmp_path):
    path = tmp_path / "tenant-state.sqlite3"
    config = PersistenceConfig("sqlite", sqlite_path=str(path))
    first = SQLiteDocumentStateRepositories(config)
    first.writer.create_document(_document("doc-a-001", "tenant-a"))
    first.writer.create_document(_document("doc-b-001", "tenant-b"))

    second = SQLiteDocumentStateRepositories(config)
    record = second.reader.get_document("doc-a-001", tenant_id="tenant-a")
    assert record.tenant_id == "tenant-a"
    assert record.workspace_id == "workspace-a"
    assert record.access_tags == ("finance",)
    assert second.reader.list_documents(DocumentQuery(tenant_id="tenant-b"), PageRequest()).total == 1
    with pytest.raises(DocumentStateError) as raised:
        second.reader.get_document("doc-a-001", tenant_id="tenant-b")
    assert raised.value.code == "not_found"


def test_sqlite_ledger_contains_additive_tenant_migration(tmp_path):
    path = tmp_path / "migration-state.sqlite3"
    config = PersistenceConfig("sqlite", sqlite_path=str(path))
    SQLiteDocumentStateRepositories(config)
    import sqlite3

    with sqlite3.connect(path) as connection:
        migrations = [row[0] for row in connection.execute(
            "SELECT migration_id FROM schema_migrations ORDER BY sequence"
        )]
        columns = {row[1] for row in connection.execute("PRAGMA table_info(documents)")}
    assert migrations == ["001_initial_document_state", "002_add_document_tenant_scope"]
    assert {"tenant_id", "workspace_id", "created_by", "updated_by", "owner_principal_id", "source_system", "access_tags_json"} <= columns
