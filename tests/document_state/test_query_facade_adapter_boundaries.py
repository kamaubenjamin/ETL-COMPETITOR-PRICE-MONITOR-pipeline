import inspect

import pytest

from src.document_state import (
    DocumentQuery as StateDocumentQuery,
    DocumentStateError,
    DocumentStateReadRepositories,
    InMemoryDocumentStateRepositories,
    PageRequest as StatePageRequest,
)
from src.document_state.adapters import DocumentStateQueryFacadeAdapter
from src.workflow_runtime.query_facade import DocumentQuery, PageRequest, QueryFacadeError


SNAPSHOT = "2026-07-13T11:00:00+00:00"


class FaultingReadRepositories:
    def __init__(self, error_code):
        self._delegate = InMemoryDocumentStateRepositories().reader
        self._error_code = error_code

    def __getattr__(self, name):
        return getattr(self._delegate, name)

    def list_documents(self, query, page):
        raise DocumentStateError(self._error_code)


def _delegate_method(name):
    def delegated(self, *args, **kwargs):
        return getattr(self._delegate, name)(*args, **kwargs)

    return delegated


for _method_name, _ in inspect.getmembers(DocumentStateReadRepositories, inspect.isfunction):
    if not _method_name.startswith("_") and _method_name != "list_documents":
        setattr(FaultingReadRepositories, _method_name, _delegate_method(_method_name))


@pytest.mark.parametrize("source_code", ["source_unavailable", "internal_error"])
def test_repository_failures_map_to_safe_facade_errors(source_code):
    source = FaultingReadRepositories(source_code)
    assert isinstance(source, DocumentStateReadRepositories)
    adapter = DocumentStateQueryFacadeAdapter(source, snapshot_at=SNAPSHOT)
    with pytest.raises(QueryFacadeError) as raised:
        adapter.list_documents(DocumentQuery(), PageRequest())
    assert raised.value.code == source_code
    payload = raised.value.to_dict()
    assert set(payload) == {"code", "message", "field"}
    assert "traceback" not in str(payload).lower()
    assert "document_state" not in str(payload).lower()


def test_invalid_query_and_not_found_errors_do_not_echo_input():
    adapter = DocumentStateQueryFacadeAdapter(
        InMemoryDocumentStateRepositories().reader,
        snapshot_at=SNAPSHOT,
    )
    with pytest.raises(QueryFacadeError) as invalid:
        adapter.list_documents(object(), PageRequest())
    assert invalid.value.code == "invalid_query"
    with pytest.raises(QueryFacadeError) as missing:
        adapter.get_document("private-document-id")
    assert missing.value.code == "not_found"
    assert "private-document-id" not in str(missing.value)


def test_adapter_does_not_expose_repository_or_mutation_surface():
    store = InMemoryDocumentStateRepositories()
    adapter = DocumentStateQueryFacadeAdapter(store.reader, snapshot_at=SNAPSHOT)
    public_names = {name for name, _ in inspect.getmembers(adapter) if not name.startswith("_")}
    assert "repositories" not in public_names
    assert not any(name.startswith(("append_", "create_", "delete_", "update_")) for name in public_names)
    assert store.reader.list_documents(StateDocumentQuery(), StatePageRequest()).total == 0
