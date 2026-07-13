import pytest

from src.document_state import DocumentRecord, InMemoryDocumentStateRepositories
from src.document_state.adapters.query_facade_adapter import DocumentStateQueryFacadeAdapter
from src.workflow_runtime.query_facade import DocumentQuery, PageRequest, QueryFacadeError


TS = "2026-07-13T12:00:00+00:00"


def _document(document_id, tenant_id):
    return DocumentRecord(
        document_id, f"{document_id}.pdf", "invoice", "received", 0.9,
        "ingest", TS, TS, TS, tenant_id=tenant_id,
    )


def test_document_state_adapter_propagates_tenant_list_and_get_filters():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(_document("doc-a-001", "tenant-a"))
    store.writer.create_document(_document("doc-b-001", "tenant-b"))
    facade = DocumentStateQueryFacadeAdapter(store.reader, snapshot_at=TS)

    result = facade.list_documents(DocumentQuery(tenant_id="tenant-a"), PageRequest())
    assert [item.document_id for item in result.items] == ["doc-a-001"]
    assert result.items[0].tenant_id == "tenant-a"
    assert facade.get_document("doc-a-001", tenant_id="tenant-a").tenant_id == "tenant-a"
    with pytest.raises(QueryFacadeError) as raised:
        facade.get_document("doc-a-001", tenant_id="tenant-b")
    assert raised.value.code == "not_found"
