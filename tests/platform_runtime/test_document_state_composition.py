from src.document_state import DocumentQuery as StateDocumentQuery
from src.document_state import DocumentRecord, PageRequest as StatePageRequest
from src.platform_runtime import (
    ApiConfig,
    AuthConfig,
    BackendConfig,
    RuntimeConfig,
    StreamlitConfig,
    compose_runtime,
)


NOW = "2026-07-14T08:00:00+00:00"
SNAPSHOT_AT = "2026-07-14T08:01:00+00:00"


def _config(mode="local", *, sqlite_path=None):
    backend = BackendConfig("sqlite", sqlite_path=str(sqlite_path)) if sqlite_path else BackendConfig("in_memory")
    guarded = mode in {"demo", "local_api_auth"}
    return RuntimeConfig(
        mode,
        backend,
        AuthConfig(
            "local_demo" if guarded else "disabled",
            identity_provider="local_demo" if guarded else "none",
            identity_provider_available=guarded,
        ),
        ApiConfig("read_only_guarded" if guarded else "read_only_unguarded"),
        StreamlitConfig("api_preview" if guarded else "local_preview"),
    )


def _record(document_id="doc-composed-001"):
    return DocumentRecord(
        document_id,
        "invoice.pdf",
        "invoice",
        "received",
        0.9,
        "received",
        NOW,
        NOW,
        NOW,
    )


def test_local_and_test_in_memory_composition():
    for mode in ("local", "test"):
        runtime = compose_runtime(_config(mode), snapshot_at=SNAPSHOT_AT)
        assert runtime.backend == "in_memory"
        assert runtime.is_durable is False


def test_explicit_sqlite_composes_for_approved_modes(tmp_path):
    for mode in ("local", "demo", "local_api_auth"):
        runtime = compose_runtime(_config(mode, sqlite_path=tmp_path / f"{mode}.sqlite3"), snapshot_at=SNAPSHOT_AT)
        assert runtime.backend == "sqlite"
        assert runtime.is_durable is True


def test_sqlite_composition_persists_across_reconstruction(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    first = compose_runtime(_config(sqlite_path=path), snapshot_at=SNAPSHOT_AT)
    first.document_state.writer.create_document(_record())
    first.close()

    second = compose_runtime(_config(sqlite_path=path), snapshot_at=SNAPSHOT_AT)
    page = second.document_state.reader.list_documents(StateDocumentQuery(), StatePageRequest())
    assert [record.document_id for record in page.items] == ["doc-composed-001"]


def test_safe_summary_redacts_sqlite_path(tmp_path):
    path = tmp_path / "private" / "runtime.sqlite3"
    path.parent.mkdir()
    runtime = compose_runtime(_config(sqlite_path=path), snapshot_at=SNAPSHOT_AT)
    summary = runtime.to_safe_dict()
    assert str(path) not in repr(runtime)
    assert str(path) not in str(summary)
    assert summary["backend"] == "sqlite"
    assert summary["config"]["backend"]["sqlite_path_configured"] is True

