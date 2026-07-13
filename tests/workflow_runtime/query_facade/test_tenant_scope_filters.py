import pytest

from src.workflow_runtime.query_facade import (
    DocumentQuery,
    InMemoryWorkflowQueryFacade,
    PageRequest,
    QueryFacadeError,
)


def test_in_memory_facade_applies_optional_tenant_narrowing():
    facade = InMemoryWorkflowQueryFacade()
    assert facade.list_documents(DocumentQuery(), PageRequest()).total == 3
    demo = facade.list_documents(DocumentQuery(tenant_id="tenant-demo"), PageRequest())
    alternate = facade.list_documents(DocumentQuery(tenant_id="tenant-alt"), PageRequest())
    assert [item.document_id for item in demo.items] == ["doc-001", "doc-002"]
    assert [item.document_id for item in alternate.items] == ["doc-003"]
    assert all(item.tenant_id == "tenant-demo" for item in demo.items)


def test_in_memory_facade_tenant_scoped_get_hides_cross_tenant_id():
    facade = InMemoryWorkflowQueryFacade()
    assert facade.get_document("doc-001", tenant_id="tenant-demo").tenant_id == "tenant-demo"
    with pytest.raises(QueryFacadeError) as raised:
        facade.get_document("doc-001", tenant_id="tenant-alt")
    assert raised.value.code == "not_found"
