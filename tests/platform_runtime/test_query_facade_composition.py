from src.document_state import DocumentRecord
from src.platform_runtime import ApiConfig, AuthConfig, BackendConfig, RuntimeConfig, StreamlitConfig, compose_runtime
from src.workflow_runtime.query_facade import DocumentQuery, PageRequest, WorkflowQueryFacadePort


NOW = "2026-07-14T10:00:00+00:00"


def _runtime():
    return compose_runtime(
        RuntimeConfig(
            "test",
            BackendConfig("in_memory"),
            AuthConfig("disabled"),
            ApiConfig("read_only_unguarded"),
            StreamlitConfig("local_preview"),
        ),
        snapshot_at=NOW,
    )


def _record(document_id, tenant_id):
    return DocumentRecord(
        document_id,
        f"{document_id}.pdf",
        "invoice",
        "received",
        0.8,
        "received",
        NOW,
        NOW,
        NOW,
        tenant_id=tenant_id,
    )


def test_query_facade_is_structurally_compatible_and_reads_selected_backend():
    runtime = _runtime()
    assert isinstance(runtime.query_facade, WorkflowQueryFacadePort)
    runtime.document_state.writer.create_document(_record("doc-a", "tenant-a"))
    page = runtime.query_facade.list_documents(DocumentQuery(), PageRequest())
    assert [item.document_id for item in page.items] == ["doc-a"]


def test_tenant_scoped_query_facade_reads_remain_narrowed():
    runtime = _runtime()
    runtime.document_state.writer.create_document(_record("doc-a", "tenant-a"))
    runtime.document_state.writer.create_document(_record("doc-b", "tenant-b"))
    page = runtime.query_facade.list_documents(DocumentQuery(tenant_id="tenant-a"), PageRequest())
    assert [item.document_id for item in page.items] == ["doc-a"]
    assert runtime.query_facade.get_document("doc-a", tenant_id="tenant-a").document_id == "doc-a"

