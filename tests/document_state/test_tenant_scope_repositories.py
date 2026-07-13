import pytest

from src.document_state import (
    DocumentQuery,
    DocumentRecord,
    DocumentStateError,
    InMemoryDocumentStateRepositories,
    PageRequest,
)


TS = "2026-07-13T12:00:00+00:00"


def _document(document_id, tenant_id):
    return DocumentRecord(
        document_id, f"{document_id}.pdf", "invoice", "received", 0.9,
        "ingest", TS, TS, TS, tenant_id=tenant_id,
    )


def test_in_memory_document_reads_narrow_by_tenant_without_changing_unscoped_preview():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(_document("doc-a-001", "tenant-a"))
    store.writer.create_document(_document("doc-b-001", "tenant-b"))

    assert store.reader.list_documents(DocumentQuery(), PageRequest()).total == 2
    tenant_a = store.reader.list_documents(DocumentQuery(tenant_id="tenant-a"), PageRequest())
    assert [item.document_id for item in tenant_a.items] == ["doc-a-001"]
    assert tenant_a.total == 1
    assert store.reader.get_document("doc-a-001", tenant_id="tenant-a").tenant_id == "tenant-a"


def test_in_memory_tenant_filter_cannot_broaden_or_disclose_cross_tenant_id():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(_document("doc-a-001", "tenant-a"))
    assert store.reader.list_documents(DocumentQuery(tenant_id="tenant-b"), PageRequest()).total == 0
    with pytest.raises(DocumentStateError) as raised:
        store.reader.get_document("doc-a-001", tenant_id="tenant-b")
    assert raised.value.code == "not_found"
