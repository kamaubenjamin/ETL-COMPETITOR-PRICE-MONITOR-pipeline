from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.providers import facade_provider
from src.api.document_intelligence.routers.documents import list_documents
from src.document_state import DocumentRecord
from src.document_state.writers import CreateDocumentCommand
from src.platform_runtime import (
    ApiConfig,
    AuthConfig,
    BackendConfig,
    RuntimeConfig,
    StreamlitConfig,
    compose_runtime,
)


NOW = "2026-07-14T12:00:00+00:00"


def _local_config(*, sqlite_path=None):
    return RuntimeConfig(
        "local",
        BackendConfig("sqlite", sqlite_path=str(sqlite_path)) if sqlite_path else BackendConfig("in_memory"),
        AuthConfig("disabled"),
        ApiConfig("read_only_unguarded"),
        StreamlitConfig("local_preview"),
    )


def _request(app, *, identity=None):
    headers = [] if identity is None else [(b"x-local-identity", identity.encode("ascii"))]
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/documents", "headers": headers, "app": app})
    request.state.request_id = "request-runtime-composition"
    return request


def test_default_app_keeps_compatibility_provider_and_behavior():
    application = create_document_intelligence_app()
    assert application.state.platform_runtime is None
    assert application.state.document_intelligence_provider is facade_provider
    assert list_documents(_request(application), status=None, document_type=None, limit=50, offset=0)["success"] is True


def test_api_can_compose_local_in_memory_and_read_writer_state():
    application = create_document_intelligence_app(runtime_config=_local_config(), snapshot_at=NOW)
    runtime = application.state.platform_runtime
    result = runtime.writers.ingestion.create_document(
        CreateDocumentCommand(
            "doc-api-runtime-001",
            "source-api-runtime-001",
            "invoice.pdf",
            "invoice",
            0.93,
            NOW,
            NOW,
            "document_engine",
        )
    )
    assert result.status == "success"
    response = list_documents(_request(application), status="received", document_type="invoice", limit=50, offset=0)
    assert [row["document_id"] for row in response["data"]] == ["doc-api-runtime-001"]
    assert "tenant_id" not in response["data"][0]


def test_api_can_compose_explicit_sqlite_and_accept_precomposed_runtime(tmp_path):
    config = _local_config(sqlite_path=tmp_path / "api-runtime.sqlite3")
    application = create_document_intelligence_app(runtime_config=config, snapshot_at=NOW)
    assert application.state.platform_runtime.backend == "sqlite"

    composed = compose_runtime(_local_config(), snapshot_at=NOW)
    from_composition = create_document_intelligence_app(runtime_composition=composed)
    assert from_composition.state.platform_runtime is composed
    assert from_composition.state.document_intelligence_provider._facade is composed.query_facade


def test_composed_api_preserves_tenant_narrowing_for_local_demo(tmp_path):
    config = RuntimeConfig(
        "local_api_auth",
        BackendConfig("sqlite", sqlite_path=str(tmp_path / "guarded.sqlite3")),
        AuthConfig("local_demo", identity_provider="local_demo", identity_provider_available=True),
        ApiConfig("read_only_guarded"),
        StreamlitConfig("api_preview"),
    )
    application = create_document_intelligence_app(runtime_config=config, snapshot_at=NOW)
    writer = application.state.platform_runtime.document_state.writer
    for document_id, tenant_id in (("doc-demo", "tenant-demo"), ("doc-other", "tenant-other")):
        writer.create_document(
            DocumentRecord(
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
        )
    response = list_documents(_request(application, identity="viewer"), status=None, document_type=None, limit=50, offset=0)
    assert [row["document_id"] for row in response["data"]] == ["doc-demo"]


def test_runtime_diagnostics_are_redacted(tmp_path):
    path = tmp_path / "private" / "api.sqlite3"
    path.parent.mkdir()
    application = create_document_intelligence_app(runtime_config=_local_config(sqlite_path=path), snapshot_at=NOW)
    assert str(path) not in str(application.state.platform_runtime_summary)
    assert str(path) not in repr(application.state.platform_runtime)

