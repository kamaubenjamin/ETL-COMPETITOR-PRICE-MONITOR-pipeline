from src.document_state.lifecycle import LifecycleAdvancementService
from src.document_state.writers import (
    AppendLifecycleEventCommand,
    CreateDocumentCommand,
    IngestionDocumentStateWriter,
    ProcessingDocumentStateWriter,
    ReviewDocumentStateWriter,
    WorkflowDocumentStateWriter,
)
from src.platform_runtime import ApiConfig, AuthConfig, BackendConfig, RuntimeConfig, StreamlitConfig, compose_runtime


NOW = "2026-07-14T09:00:00+00:00"
LATER = "2026-07-14T09:01:00+00:00"


def _runtime():
    config = RuntimeConfig(
        "local",
        BackendConfig("in_memory"),
        AuthConfig("disabled"),
        ApiConfig("read_only_unguarded"),
        StreamlitConfig("local_preview"),
    )
    return compose_runtime(config, snapshot_at=LATER)


def test_all_writers_and_one_lifecycle_service_are_composed():
    runtime = _runtime()
    assert isinstance(runtime.lifecycle, LifecycleAdvancementService)
    assert isinstance(runtime.writers.ingestion, IngestionDocumentStateWriter)
    assert isinstance(runtime.writers.processing, ProcessingDocumentStateWriter)
    assert isinstance(runtime.writers.review, ReviewDocumentStateWriter)
    assert isinstance(runtime.writers.workflow, WorkflowDocumentStateWriter)


def test_writer_append_advances_projection_visible_through_query_facade():
    runtime = _runtime()
    create = CreateDocumentCommand(
        "doc-wired-001",
        "source-received-001",
        "invoice.pdf",
        "invoice",
        0.91,
        NOW,
        NOW,
        "document_engine",
    )
    assert runtime.writers.ingestion.create_document(create).status == "success"

    event = AppendLifecycleEventCommand(
        "event-classified-001",
        "source-classified-001",
        "doc-wired-001",
        "classified",
        LATER,
        "document_engine",
        "classification",
    )
    assert runtime.writers.ingestion.append_lifecycle_event(event).status == "success"

    stored = runtime.document_state.reader.get_document("doc-wired-001")
    projected = runtime.query_facade.get_document("doc-wired-001")
    assert (stored.status, stored.current_stage, stored.version) == ("classified", "classification", 2)
    assert (projected.status, projected.current_stage) == ("classified", "classification")

